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

Tool to calculate Requests Per Second since startup for a given HBase table region using JMX API stats

Designed to help analyze region hotspotting

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
import requests
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import validate_host, validate_port, validate_chars
    from harisekhon.utils import UnknownError, CriticalError, support_msg_api, printerr
    from harisekhon import CLI, RequestHandler
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2'


class HBaseCalculateTableRegionsRequestsPerSec(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseCalculateTableRegionsRequestsPerSec, self).__init__()
        # Python 3.x
        # super().__init__()
        self.host_list = []
        self.port = 16030
        self.table = None
        self.namespace = 'default'
        self.timeout_default = 300
        self._regions = None

    def add_options(self):
        self.add_opt('-P', '--port', default=self.port, help='HBase RegionServer port (default: {})'.format(self.port))
        self.add_opt('-T', '--table', help='Table name')
        self.add_opt('-N', '--namespace', default=self.namespace, help='Namespace (default: {})'.format(self.namespace))

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
        self.namespace = self.get_opt('namespace')
        validate_chars(self.namespace, 'hbase namespace', 'A-Za-z0-9:._-')

    def run(self):
        for host in self.host_list:
            try:
                self.print_region_stats(host)
            except (CriticalError, UnknownError, requests.RequestException) as _:
                printerr("ERROR querying JMX stats for host '{}': {}".format(host, _), )

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
            raise UnknownError("failed to find uptime in JMX stats for host '{}'. {}".format(host, support_msg_api()))

        region_regex = re.compile('^Namespace_{namespace}_table_{table}_region_(.+)_metric_(.+)RequestCount'\
                                  .format(namespace=self.namespace, table=self.table))
        for bean in beans:
            if bean['name'] == 'Hadoop:service=HBase,name=RegionServer,sub=Regions':
                for key in sorted(bean):
                    match = region_regex.match(key)
                    if match:
                        region = match.group(1)
                        metric = match.group(2)
                        print('{:20s}\t{:20s}\t\t{:10s}\t{:8.0f}'.format(host, region, metric, bean[key] / uptime))

    # some extra effort to make it look the same as HBase presents it as
    #def encode_char(self, char):
    #    if char in string.printable and char not in ('\t', '\n', '\r', '\x0b', '\x0c'):
    #        return char
    #    _ = '{0:#0{1}x}'.format(ord(char), 4).replace('0x', '\\x')
    #    _ = self.re_hex.sub(lambda x: x.group(1).upper(), _)
    #    return _


if __name__ == '__main__':
    HBaseCalculateTableRegionsRequestsPerSec().main()
