#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-09-29 15:00:36 +0100 (Thu, 29 Sep 2016)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

r"""

Tool to return the first available healthy server or active master from a given list

Configurable test criteria: TCP socket, HTTP, HTTPS, Ping, URL with optional Regex content match.

Can mix and match between a comma separated list of hosts (--host server1,server2,server3... or contents of the $HOST
environment variable if not specified) and general free-form space separated arguments, which is useful if piping
a host list through xargs.

Multi-threaded for speed and exits upon first available host response to minimize delay to ~ 1 second or less.

Useful for pre-determining a server to be passed to tools that only take a single --host argument but for which the
technology has later added multi-master support or active-standby masters (eg. Hadoop, HBase) or where you want to
query cluster wide information available from any online peer (eg. Elasticsearch).


Examples:


Return first web server to respond:

    cat host_list.txt | xargs ./find_active_server.py --http


More specific examples follow, and they have more specialised subclassed programs in each example so you don't need
to use all the switches from find_active_server.py


Target a Nagios Plugin to first available cluster node, eg. Elasticsearch check from Advanced Nagios Plugins Collection:

    ./check_elasticsearch_cluster_status.pl --host $(./find_active_server.py -v --http --port 9200  node1 node2 node3)

    ./find_active_elasticsearch_node.py  node1 node2 node3


Find a SolrCloud node:

    ./find_active_server.py --http --url /solr/ --regex 'Solr Admin'  node1 node2

    ./find_active_solrcloud_node.py  node1 node2


Find the active Hadoop NameNode in a High Availability cluster:

    ./find_active_server.py --http --port 50070 \
                            --url 'jmx?qry=Hadoop:service=NameNode,name=NameNodeStatus' \
                            --regex '"State"\s*:\s*"active"' \
                            namenode1 namenode2

    ./find_active_hadoop_namenode.py  namenode1 namenode2


Find the active Hadoop Yarn Resource Manager in a High Availability cluster:

    ./find_active_server.py --http --port 8088 \
                            --url /ws/v1/cluster \
                            --regex '"haState"\s*:\s*"ACTIVE"' \
                            resourcemanager1 resourcemanager2

    ./find_active_hadoop_yarn_resource_manager.py  resourcemanager1 resourcemanager2


Find the active HBase Master in a High Availability cluster:

    ./find_active_server.py --http --port 16010 \
                            --url '/jmx?qry=Hadoop:service=HBase,name=Master,sub=Server' \
                            --regex '"tag.isActiveMaster" : "true"' \
                            hmaster1 hmaster2

    ./find_active_hbase_master.py  hmaster1 hmaster2


By default checks the same --port on all servers. Hosts may have optional :<port> suffixes added to individually
override each one.

Exits with return code 1 and NO_AVAILABLE_SERVER if none of the supplied servers pass the test criteria,
--quiet mode will return blank output and exit code 1 in that case.


See also Advanced HAProxy configurations (part of the Advanced Nagios Plugins Collection) at:

    https://github.com/harisekhon/haproxy-configs

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import os
import platform
import re
import socket
import subprocess
import sys
#from threading import Thread
from multiprocessing.pool import ThreadPool
from multiprocessing import cpu_count
# prefer blocking semantics of que.get() rather than handling deque.popleft() => 'IndexError: pop from an empty deque'
#from collections import deque
import traceback
from random import shuffle
# Python 2 Queue vs Python 3 queue module :-/
if sys.version[0] == '2':
    import Queue as queue  # pylint: disable=import-error
else:
    import queue as queue  # pylint: disable=import-error
try:
    # false positive from pylint, queue is imported first
    import requests  # pylint: disable=wrong-import-order
except ImportError:
    print(traceback.format_exc(), end='')
    sys.exit(4)
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, log_option, die, code_error, uniq_list_ordered
    from harisekhon.utils import validate_hostport_list, validate_port, validate_int, validate_regex
    from harisekhon.utils import isPort, isInt, isStr, isTuple, UnknownError
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.8.6'


class FindActiveServer(CLI):

    def __init__(self):
        # Python 2.x
        super(FindActiveServer, self).__init__()
        # Python 3.x
        # super().__init__()
        self.host_list = []
        self.default_port = 80
        self.port = self.default_port
        self.protocol = None
        self.url_path = None
        self.regex = None
        self.request_timeout = None
        self.default_num_threads = min(cpu_count() * 4, 100)
        self.num_threads = None
        self.queue = queue.Queue()
        self.pool = None

    def add_options(self):
        self.add_hostoption(name='', default_port=self.default_port)
        self.add_opt('-p', '--ping', action='store_true', help='Ping the server only, no socket connection')
        self.add_opt('-w', '--http', action='store_true',
                     help='Fetch web page over HTTP protocol instead of doing a socket test')
        self.add_opt('-s', '--https', action='store_true',
                     help='Fetch web page over HTTPS protocol instead of doing a socket test ' +
                     '(overrides --http, changes port 80 to 443)')
        self.add_opt('-u', '--url', help='URL path to fetch (implies --http)')
        self.add_opt('-r', '--regex',
                     help='Regex to search for in http content (optional). Case sensitive by default ' + \
                          'for better targeting, wrap with (?i:...) modifier for case insensitivity')
        self.add_common_opts()

    # only here for subclassed programs convenience
    def add_ssl_opt(self):
        self.add_opt('-S', '--ssl', action='store_true', help='Use SSL')

    def add_common_opts(self):
        if self.is_option_defined('ssl'):
            if self.get_opt('ssl'):
                self.protocol = 'https'
                log_option('SSL', 'true')
            else:
                log_option('SSL', 'false')
        self.add_opt('-q', '--quiet', action='store_true', help='Returns no output instead of NO_AVAILABLE_SERVER '\
                                                              + '(convenience for scripting)')
        self.add_opt('-n', '--num-threads', default=self.default_num_threads, type='int',
                     help='Number or parallel threads to speed up processing ' + \
                          '(default is 4 times number of cores: {}), '.format(self.default_num_threads) + \
                          'use -n=1 for deterministic host preference order [slower])')
        self.add_opt('-T', '--request-timeout', metavar='secs', type='int', default=os.getenv('REQUEST_TIMEOUT', 2),
                     help='Timeout for each individual server request in seconds ($REQUEST_TIMEOUT, default: 2 secs)')
        self.add_opt('-R', '--random', action='store_true', help='Randomize order of hosts tested ' +
                     '(for use with --num-threads=1)')

    def process_options(self):
        self.validate_common_opts()

    def validate_common_opts(self):
        hosts = self.get_opt('host')
        self.port = self.get_opt('port')
        if hosts:
            self.host_list = [host.strip() for host in hosts.split(',') if host]
        self.host_list += self.args
        self.host_list = uniq_list_ordered(self.host_list)
        if not self.host_list:
            self.usage('no hosts specified')
        validate_hostport_list(self.host_list, port_optional=True)
        validate_port(self.port)
        self.port = int(self.port)
        self.validate_protocol_opts()
        self.validate_misc_opts()

    def validate_protocol_opts(self):
        if self.is_option_defined('https') and self.get_opt('https'):
            self.protocol = 'https'
            # optparse returns string, even though default we gave from __init__ was int
            # comparison would fail without this cast
            if str(self.port) == '80':
                log.info('overriding port 80 => 443 for https')
                self.port = 443
        elif self.is_option_defined('http') and self.get_opt('http'):
            self.protocol = 'http'
            if not self.port:
                self.port = 80
        if self.is_option_defined('url') and self.get_opt('url'):
            self.url_path = self.get_opt('url')
        if self.url_path:
            if self.protocol is None:
                self.protocol = 'http'
            elif self.protocol == 'ping':
                self.usage('cannot specify --url-path with --ping, mutually exclusive options!')
        if self.is_option_defined('ping') and self.get_opt('ping'):
            if self.protocol:
                self.usage('cannot specify --ping with --http / --https, mutually exclusive tests!')
            elif self.port != self.default_port:
                self.usage('cannot specify --port with --ping, mutually exclusive options!')
            self.protocol = 'ping'
        if self.protocol and self.protocol not in ('http', 'https', 'ping'):
            code_error('invalid protocol, must be one of http / https / ping')

    def validate_misc_opts(self):
        if self.is_option_defined('regex') and self.get_opt('regex'):
            self.regex = self.get_opt('regex')
        if self.regex:
            if not self.protocol:
                self.usage('--regex cannot be used without --http / --https')
            validate_regex(self.regex)
            self.regex = re.compile(self.regex)

        self.num_threads = self.get_opt('num_threads')
        validate_int(self.num_threads, 'num threads', 1, 100)
        self.num_threads = int(self.num_threads)

        self.request_timeout = self.get_opt('request_timeout')
        validate_int(self.request_timeout, 'request timeout', 1, 60)
        self.request_timeout = int(self.request_timeout)

        if self.get_opt('random'):
            log_option('random', True)
            shuffle(self.host_list)

    def run(self):
        self.pool = ThreadPool(processes=self.num_threads)
        if self.protocol in ('http', 'https'):
            for host in self.host_list:
                (host, port) = self.port_override(host)
                #if self.check_http(host, port, self.url_path):
                #    self.finish(host, port)
                self.launch_thread(self.check_http, host, port, self.url_path)
        elif self.protocol == 'ping':
            for host in self.host_list:
                # this strips the :port from host
                (host, port) = self.port_override(host)
                #if self.check_ping(host):
                #    self.finish(host)
                self.launch_thread(self.check_ping, host, 1, self.request_timeout)
        else:
            for host in self.host_list:
                (host, port) = self.port_override(host)
                #if self.check_socket(host, port):
                #    self.finish(host, port)
                self.launch_thread(self.check_socket, host, port)
        self.collect_results()
        if not self.get_opt('quiet'):
            print('NO_AVAILABLE_SERVER')
        sys.exit(1)

    def launch_thread(self, func, *args):
        # works but no tunable concurrency
        #_ = Thread(target=lambda q, arg1: q.put(self.check_ping(arg1)), args=(que, host))
        #_ = Thread(target=lambda: que.put(self.check_ping(host)))
        #_.daemon = True
        #_.start()
        #if self.num_threads == 1:
        #    _.join()
        #
        # blocks and prevents concurrency, use que instead
        #async_result = pool.apply_async(self.check_ping, (host,))
        #return_val = async_result.get()
        #
        self.pool.apply_async(lambda *args: self.queue.put(func(*args)), args)

    def collect_results(self):
        return_val = None
        for _ in self.host_list:
            return_val = self.queue.get()
            if return_val:
                break
        if return_val:
            if isTuple(return_val):
                self.finish(*return_val)
            elif isStr(return_val):
                self.finish(return_val)
            else:
                code_error('collect_results() found non-tuple / non-string on queue')

    def port_override(self, host):
        port = self.port
        if ':' in host:
            parts = host.split(':')
            if len(parts) == 2:
                port = parts[1]
                if not isPort(port):
                    die('error in host definition, not a valid port number: \'{0}\''.format(host))
            else:
                die('error in host definition, contains more than one colon: \'{0}\''.format(host))
            host = parts[0]
        return (host, port)

    def finish(self, host, port=None):
        print(host, end='')
        if port is not None and port != self.port:
            print(':{0}'.format(port), end='')
        print()
        sys.exit(0)

    @staticmethod
    def check_ping(host, count=None, wait=None):
        if count is None:
            count = 1
        if wait is None:
            wait = 3
        if not isInt(count):
            raise UnknownError("passed invalid count '{0}' to check_ping method, must be a valid integer!"\
                               .format(count))
        if not isInt(wait):
            raise UnknownError("passed invalid wait '{0}' to check_ping method, must be a valid integer!"\
                               .format(wait))
        log.info("pinging host '%s' (count=%s, wait=%s)", host, count, wait)
        count_switch = '-c'
        if platform.system().lower() == 'windows':
            count_switch = '-n'
        wait_switch = '-w'
        if platform.system().lower() == 'darwin':
            wait_switch = '-W'
        # causes hang if count / wait are not cast to string
        cmd = ['ping', count_switch, '{0}'.format(count), wait_switch, '{0}'.format(wait), host]
        log.debug('cmd: %s', ' '.join(cmd))
        #log.debug('args: %s', cmd)
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            #log.debug('communicating')
            (stdout, stderr) = process.communicate()
            #log.debug('waiting for child process')
            process.wait()
            exitcode = process.returncode
            log.debug('stdout: %s', stdout)
            log.debug('stderr: %s', stderr)
            log.debug('exitcode: %s', exitcode)
            if exitcode == 0:
                log.info("host '%s' responded to ping", host)
                return host
        except subprocess.CalledProcessError as _:
            log.warn('ping failed: %s', _.output)
        except OSError as _:
            die('error calling ping: {0}'.format(_))
        return None

    def check_socket(self, host, port):
        log.info("checking host '%s' port '%s' socket", host, port)
        try:
            #log.debug('creating socket')
            #sock = socket.socket()
            #log.info("connecting to '%s:%s'", host, port)
            #sock.connect((host, int(port)))
            socket.create_connection((host, int(port)), self.request_timeout)
            #sock.close()
            log.info("socket connected to host '%s' port '%s'", host, port)
            return (host, port)
        except IOError:
            return None

    def check_http(self, host, port, url_path=''):
        if not isStr(url_path):
            url_path = ''
        url = '{protocol}://{host}:{port}/{url_path}'.format(protocol=self.protocol,
                                                             host=host,
                                                             port=port,
                                                             url_path=url_path.lstrip('/'))
        log.info('GET %s', url)
        try:
            # timeout here isn't total timeout, it's response time
            req = requests.get(url, timeout=self.request_timeout)
        except requests.exceptions.RequestException as _:
            log.info('%s - returned exception: %s', url, _)
            return False
        except IOError as _:
            log.info('%s - returned IOError: %s', url, _)
            return False
        log.debug("%s - response: %s %s", url, req.status_code, req.reason)
        log.debug("%s - content:\n%s\n%s\n%s", url, '='*80, req.content.strip(), '='*80)
        if req.status_code != 200:
            log.info('%s - status code %s != 200', url, req.status_code)
            return None
        if self.regex:
            log.info('%s - checking regex against content', url)
            # if this ends up not being processed properly and remains a string instead
            # of the expected compiled regex, then .search() will hang
            if isStr(self.regex):
                die('string found instead of expected compiled regex!')
            if self.regex.search(req.content):
                log.info('%s - regex matched http output', url)
            else:
                log.info('%s - regex did not match http output', url)
                return None
        log.info("%s - passed all checks", url)
        return (host, port)


if __name__ == '__main__':
    FindActiveServer().main()
