#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-09-29 15:00:36 +0100 (Thu, 29 Sep 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to return the first available healthy server or active master from a given list

Useful for pre-determining a server to be passed to tools that only take a single --host argument but for which the
technology has later added multi-master support or active-standby masters (eg. Hadoop, HBase) or where you want to
query cluster wide information available from any online peer (eg. Elasticsearch).

example using the Advanced Nagios Plugins Collection:

./check_elasticsearch_cluster_status.pl --host $(./find_active_server.py -v --http --port 9200 node1 node2 node3 node4 ...)

Configurable tests include socket, http, https, ping, url and/or regex content match.

Multi-threaded for speed and exits with first result to not significantly delay the top level tool it's called for
by more than ~ 1 second.

By default checks the same --port on all servers. Hosts may have optional :<port> suffixes added to override them.

Exits with return code 1 and no output by if none of the supplied servers pass the test criteria, --verbose mode will
output the token NO_AVAILABLE_SERVER.

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
# prefer blocking semantics of que.get() rather than handling deque.popleft() => 'IndexError: pop from an empty deque'
#from collections import deque
import Queue
import traceback
from random import shuffle
try:
    #from bs4 import BeautifulSoup
    import requests
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
    from harisekhon.utils import isPort, isStr, isTuple
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.3'


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
        self.url_suffix = None
        self.regex = None
        self.request_timeout = 1
        self.num_threads = 10
        self.que = Queue.Queue()
        self.pool = None

    def add_options(self):
        self.add_hostoption(name='', default_port=self.default_port)
        self.add_opt('-p', '--ping', action='store_true', help='Ping the server only, no socket connection')
        self.add_opt('-w', '--http', action='store_true',
                     help='Fetch web page over HTTP protocol instead of doing a socket test')
        self.add_opt('-s', '--https', action='store_true',
                     help='Fetch web page over HTTPS protocol instead of doing a socket test ' +
                     '(overrides --http, changes port 80 to 443)')
        self.add_opt('-u', '--url', help='URL suffix to fetch (implies --http)')
        self.add_opt('-r', '--regex', help='Regex to search for in http content (optional)')
        self.add_opt('-n', '--num-threads', default=self.num_threads, type='int',
                     help='Number or parallel threads to speed up processing (default: 10, ' +
                     'use -n=1 for deterministic host preference order [slower])')
        self.add_opt('-R', '--random', action='store_true', help='Randomize order of hosts tested ' +
                     '(for use with --num-threads=1)')
        self.add_opt('-T', '--request-timeout', metavar='secs', type='int',
                     help='Timeout for each individual server request in seconds (default: 1 second)')

    def process_options(self):
        hosts = self.get_opt('host')
        self.port = self.get_opt('port')
        self.url_suffix = self.get_opt('url')
        self.regex = self.get_opt('regex')
        self.num_threads = self.get_opt('num_threads')
        if hosts:
            self.host_list = [host.strip() for host in hosts.split(',') if host]
        self.host_list += self.args
        self.host_list = uniq_list_ordered(self.host_list)
        if self.get_opt('random'):
            log_option('random', True)
            shuffle(self.host_list)
        if self.get_opt('https'):
            self.protocol = 'https'
            # optparse returns string, even though default we gave from __init__ was int
            # comparison would fail without this cast
            if str(self.port) == '80':
                log.info('overriding port 80 => 443 for https')
                self.port = 443
        elif self.get_opt('http'):
            self.protocol = 'http'
            if not self.port:
                self.port = 80
        if self.get_opt('ping'):
            if self.protocol:
                self.usage('cannot specify --ping with --http / --https, mutually exclusive tests!')
            elif self.port != self.default_port:
                self.usage('cannot specify --port with --ping, mutually exclusive options!')
            self.protocol = 'ping'
        if self.url_suffix:
            if self.protocol is None:
                self.protocol = 'http'
            elif self.protocol == 'ping':
                self.usage('cannot specify --url-suffix with --ping, mutually exclusive options!')
        self.validate_options()

    def validate_options(self):
        if not self.host_list:
            self.usage('no hosts specified')
        validate_hostport_list(self.host_list, port_optional=True)
        validate_port(self.port)
        if self.protocol:
            if self.protocol not in ('http', 'https', 'ping'):
                code_error('invalid protocol, must be one of http or https')
        if self.regex:
            if not self.protocol:
                self.usage('--regex cannot be used without --http / --https')
            validate_regex(self.regex)
            self.regex = re.compile(self.regex)
        validate_int(self.num_threads, 'num threads', 1, 100)

    def run(self):
        self.pool = ThreadPool(processes=self.num_threads)
        if self.protocol in ('http', 'https'):
            for host in self.host_list:
                (host, port) = self.port_override(host)
                #if self.check_http(host, port, self.url_suffix):
                #    self.finish(host, port)
                self.launch_thread(self.check_http, host, port, self.url_suffix)
        elif self.protocol == 'ping':
            for host in self.host_list:
                # this strips the :port from host
                (host, port) = self.port_override(host)
                #if self.check_ping(host):
                #    self.finish(host)
                self.launch_thread(self.check_ping, host)
        else:
            for host in self.host_list:
                (host, port) = self.port_override(host)
                #if self.check_socket(host, port):
                #    self.finish(host, port)
                self.launch_thread(self.check_socket, host, port)
        self.collect_results()
        if self.verbose:
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
        self.pool.apply_async(lambda *args: self.que.put(func(*args)), args)

    def collect_results(self):
        return_val = None
        for _ in range(len(self.host_list)):
            return_val = self.que.get()
            if return_val:
                break
        if return_val:
            if isTuple(return_val):
                self.finish(*return_val)
            elif isStr(return_val):
                self.finish(return_val)
            else:
                code_error('collect_results() found non-tuple / non-string on que')

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
            print(':{0}'.format(port))
        print()
        sys.exit(0)

    @staticmethod
    def check_ping(host, count=1, wait=1):
        log.info("pinging host '%s' (count=%s, wait=%s)", host, count, wait)
        ping_count = '-c {0}'.format(count)
        if platform.system().lower() == 'windows':
            ping_count = '-n 1'
        ping_wait = '-w {0}'.format(wait)
        if platform.system().lower() == 'darwin':
            ping_wait = '-W 1'
        try:
            exitcode = subprocess.call(["ping", ping_count, ping_wait, host],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if exitcode == 0:
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
            return (host, port)
        except IOError:
            return None

    def check_http(self, host, port, url_suffix=''):
        if not isStr(url_suffix):
            url_suffix = ''
        url = '{protocol}://{host}:{port}/{url_suffix}'.format(protocol=self.protocol,
                                                               host=host,
                                                               port=port,
                                                               url_suffix=url_suffix.lstrip('/'))
        log.info('GET %s', url)
            # timeout here isn't total timeout, it's response time
        try:
            req = requests.get(url, timeout=self.request_timeout)
        except requests.exceptions.RequestException:
            return False
        log.debug("response: %s %s", req.status_code, req.reason)
        log.debug("content:\n%s\n%s\n%s", '='*80, req.content.strip(), '='*80)
        if req.status_code != 200:
            return None
        if self.regex:
            log.info('checking regex against content')
            if self.regex.search(req.content):
                log.info('matched regex in http output')
            else:
                log.info('regex match not found in http output')
                return None
        return (host, port)


if __name__ == '__main__':
    FindActiveServer().main()
