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

Tool to find which server from a list is active / alive / master

Generic tool written to be used to extend single server written tools by finding and returning the first alive server
or the first server which is the active master in a cluster

Can be used to extend other command lines tools that only accept one server parameter to pre-select which server the
tool should contact

Good for extending Nagios Plugins and other CLI tools that only take a single server parameter by pre-selecting which
server they should contact, either via a socket check or http(s) with optional content regex matching to be able to
determine the current master.

Use --random to randomize the test order, returns the first randomly available server (that also matches the criteria
if --url / --regex are specified)

By default checks the same --port on all servers. Hosts may have optional :<port> suffixes added to override them

Exits with return code 1 and no output if none of the supplied --host or args are available on the given port

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
    from harisekhon.utils import validate_hostport_list, validate_port, isPort, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'


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
        self.timeout_default = 60
        self.verbose_default = 1

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
        self.add_opt('-R', '--random', action='store_true', help='Randomize order of hosts tested')
        self.add_opt('-T', '--request-timeout', metavar='secs',
                     help='Timeout for each individual server request in seconds (default: 1 second)')

    def process_options(self):
        hosts = self.get_opt('host')
        self.port = self.get_opt('port')
        self.url_suffix = self.get_opt('url')
        self.regex = self.get_opt('regex')
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

    def run(self):
        if self.protocol in ('http', 'https'):
            for host in self.host_list:
                (host, port) = self.port_override(host)
                if self.check_http(host, port, self.url_suffix):
                    self.finish(host, port)
        elif self.protocol == 'ping':
            for host in self.host_list:
                (host, port) = self.port_override(host)
                if self.check_ping(host):
                    self.finish(host)
        else:
            for host in self.host_list:
                (host, port) = self.port_override(host)
                if self.check_socket(host, port):
                    self.finish(host, port)
        sys.exit(1)

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
        log.info("pinging host '%s'", host)
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
                return True
        except subprocess.CalledProcessError as _:
            log.warn('ping failed: %s', _.output)
        except OSError as _:
            die('error calling ping: {0}'.format(_))
        return False

    def check_socket(self, host, port):
        log.info("checking host '%s' port '%s' socket", host, port)
        try:
            #log.debug('creating socket')
            #sock = socket.socket()
            log.info(r'connecting to \'%s\:%s\'', host, port)
            #sock.connect((host, int(port)))
            socket.create_connection((host, int(port)), self.request_timeout)
            #sock.close()
            return True
        except IOError:
            return False

    def check_http(self, host, port, url_suffix=''):
        if url_suffix is None:
            url_suffix = ''
        url = '{protocol}://{host}:{port}/{url_suffix}'.format(protocol=self.protocol,
                                                               host=host,
                                                               port=port,
                                                               url_suffix=url_suffix)
        log.info('GET %s', url)
            # timeout here isn't total timeout, it's response time
        try:
            req = requests.get(url, timeout=self.request_timeout)
        except requests.exceptions.RequestException:
            return False
        log.debug("response: %s %s", req.status_code, req.reason)
        log.debug("content:\n%s\n%s\n%s", '='*80, req.content.strip(), '='*80)
        if req.status_code != 200:
            return False
        if self.regex:
            log.info('checking regex against content')
            if self.regex.search(req.content):
                log.info('matched regex in http output')
            else:
                log.info('regex match not found in http output')
                return False
        return True


if __name__ == '__main__':
    FindActiveServer().main()
