#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-06 10:42:59 +0100 (Thu, 06 Oct 2016)
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

Tool to show requests per second per HBase table region from JMX API stats

Designed to help analyze region hotspotting by looking at requests per second

Argument list should be one or more RegionServers to dump the JMX stats from

Tested on Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2, 1.3.1

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import json
#import logging
import os
import re
import sys
import traceback
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import validate_host, validate_port, validate_chars, support_msg_api, UnknownError
    from harisekhon import CLI, RequestHandler
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'


class HBaseCalculateTableRegionsRequestsPerSec(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseCalculateTableRegionsRequestsPerSec, self).__init__()
        # Python 3.x
        # super().__init__()
        self.host_list = []
        self.port = 16301
        self.table = None
        self.namespace = '.*'
        self.timeout_default = 300
        #self.re_hex = re.compile('([a-f]+)') # to convert to uppercase later for aesthetics
        self._regions = None

    def add_options(self):
        self.add_opt('-P', '--port', default=self.port, help='HBase RegionServer port (default: {})'.format(self.port))
        self.add_opt('-T', '--table', help='Table name')
        #self.add_opt('-N', '--namespace', default='Default', help='Namespace (default: Default)')

    def process_args(self):
        #log.setLevel(logging.INFO)
        self.host_list = self.args
        if not self.host_list:
            self.usage('no host arguments given, must give at least one regionserver host as an argument')
        for host in self.host_list:
            validate_host(host)
        self.port = self.get_opt('port')
        validate_port(self.port)
        self.table = self.get_opt('table')
        validate_chars(self.table, 'hbase table', 'A-Za-z0-9:._-')
        #self.namespace = self.get_opt('namespace')
        #validate_chars(self.namespace, 'hbase namespace', 'A-Za-z0-9:._-')

    def run(self):
#        region_header = 'Region'
#        start_key_header = 'Start Key'
#        end_key_header = 'End Key'
#        server_header = 'Server (host:port)'
#        separator = '    '
#        region_width = len(self.region_header)
#        start_key_width = len(self.start_key_header)
#        end_key_width = len(self.end_key_header)
#        server_width = len(self.server_header)
#        total_width = (self.region_width + self.server_width +
#                            self.start_key_width + self.end_key_width +
#                            len(3 * self.separator))
        # use built-in pylib's request handler and CLI exception handlers error catching, keep code here short
        for host in self.host_list:
            self.print_region_stats(host)

    def print_region_stats(self, host):
        req = RequestHandler().get('http://{host}:{port}/jmx'.format(host=host, port=self.port))
        json_data = json.loads(req.text)
        uptime = None
        beans = json_data['beans']
        for bean in beans:
            if bean['name'] == 'java.lang:type=Runtime':
                uptime = int(bean['Uptime'] / 1000)
                break
        if not uptime:
            raise UnknownError('failed to find uptime in JMX stats. {}'.format(support_msg_api()))

        region_regex = re.compile('^Namespace_{namespace}_table_{table}_region_(.+)_metric_.*RequestCount'\
                                  .format(namespace=self.namespace, table=self.table))
        for bean in beans:
            if bean['name'] == 'Hadoop:service=HBase,name=RegionServer,sub=Regions':
                for key in bean:
                    match = region_regex.match(key)
                    if match:
                        print('{}\t{:.1f}'.format(match.group(1), bean[key] / uptime))

    # some extra effort to make it look the same as HBase presents it as
    #def encode_char(self, char):
    #    if char in string.printable and char not in ('\t', '\n', '\r', '\x0b', '\x0c'):
    #        return char
    #    _ = '{0:#0{1}x}'.format(ord(char), 4).replace('0x', '\\x')
    #    _ = self.re_hex.sub(lambda x: x.group(1).upper(), _)
    #    return _

if __name__ == '__main__':
    HBaseCalculateTableRegionsRequestsPerSec().main()
