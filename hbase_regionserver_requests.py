#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-06 10:42:59 +0100 (Thu, 06 Oct 2016)
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

"""

Tool to calculate HBase RegionServer Requests Per Second or Average Since Startup using JMX API stats

Designed to help analyze regionserver load imbalance (see also hbase_region_requests.py for region hotspotting)

Argument list should be one or more RegionServers to dump the JMX stats from

Tested on Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2, 1.3.1

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import os
import re
import sys
import time
import traceback
import requests
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import validate_host, validate_port, validate_int
    from harisekhon.utils import UnknownError, CriticalError, support_msg_api, printerr, plural, log
    from harisekhon import CLI, RequestHandler
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.5.3'


class HBaseRegionServerRequests(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseRegionServerRequests, self).__init__()
        # Python 3.x
        # super().__init__()
        self.host_list = []
        self.port = 16030
        self.interval = 1
        self.count = 0
        self.since_uptime = False
        self.stats = {}
        self.last = {}
        self.first_iteration = 0
        self.request_type = None
        self.request_types = ('read', 'write', 'total', 'rpcScan', 'rpcMutate', 'rpcMulti', 'rpcGet', 'blocked')
        self.timeout_default = 300
        self.url = None
        self._regions = None

    def add_options(self):
        self.add_opt('-P', '--port', default=os.getenv('HBASE_REGIONSERVER_PORT', self.port),
                     help='HBase RegionServer port (default: {})'.format(self.port))
        self.add_opt('-i', '--interval', default=self.interval,
                     help='Interval to print rates at (default: {})'.format(self.interval))
        self.add_opt('-c', '--count', default=self.count,
                     help='Number of times to print stats (default: {}, zero means infinite)'.format(self.count))
        self.add_opt('-a', '--average', action='store_true', help='Calculate average since RegionServer startup')
        self.add_opt('-T', '--type', help='Only return given metric types (comma separated list containing any of: {})'\
                                          .format(', '.join(self.request_types)))

    def process_args(self):
        self.host_list = self.args
        if not self.host_list:
            self.usage('no host arguments given, must give at least one regionserver host as an argument')
        for host in self.host_list:
            validate_host(host)
        self.port = self.get_opt('port')
        validate_port(self.port)

        self.interval = self.get_opt('interval')
        self.count = self.get_opt('count')
        self.since_uptime = self.get_opt('average')
        validate_int(self.interval, 'interval')
        validate_int(self.count, 'count')
        self.interval = int(self.interval)
        self.count = int(self.count)
        if self.count == 0:
            self.disable_timeout()
        self.request_type = self.get_opt('type')
        if self.request_type:
            self.request_type = [_.strip() for _ in self.request_type.split(',')]
            for _ in self.request_type:
                if _ not in self.request_types:
                    self.usage('--type may only include: {}'.format(', '.join(self.request_types)))

    def run(self):
        if self.count:
            for _ in range(self.count):
                self.run_hosts()
                if _ != self.count - 1:
                    time.sleep(self.interval)
        else:
            while True:
                self.run_hosts()
                time.sleep(self.interval)

    def run_hosts(self):
        for host in self.host_list:
            url = 'http://{host}:{port}/jmx'.format(host=host, port=self.port)
            if not self.since_uptime:
                url += '?qry=Hadoop:service=HBase,name=RegionServer,sub=Server'
            try:
                self.run_host(host, url)
            except (CriticalError, UnknownError, requests.RequestException) as _:
                printerr("ERROR querying JMX stats for host '{}': {}".format(host, _), )

    def run_host(self, host, url):
        log.info('querying %s', host)
        req = RequestHandler().get(url)
        json_data = json.loads(req.text)
        uptime = None
        beans = json_data['beans']
        if self.since_uptime:
            for bean in beans:
                if bean['name'] == 'java.lang:type=Runtime':
                    uptime = int(bean['Uptime'] / 1000)
                    break
            if not uptime:
                raise UnknownError("failed to find uptime in JMX stats for host '{}'. {}"\
                                   .format(host, support_msg_api()))
        for bean in beans:
            log.debug('processing Regions bean')
            if bean['name'] == 'Hadoop:service=HBase,name=RegionServer,sub=Server':
                self.process_bean(host, bean, uptime)
                self.print_stats(host)

    def process_bean(self, host, bean, uptime):
        region_regex = re.compile('^(.+)RequestCount$')
        stats = self.stats
        last = self.last
        for key in bean:
            match = region_regex.match(key)
            if match:
                metric_type = match.group(1)
                log.info('matched regionserver %s %s request count = %s', host, metric_type, bean[key])
                if host not in stats:
                    stats[host] = {}
                if host not in last:
                    last[host] = {}
                if self.request_type and metric_type not in self.request_type:
                    continue
                if self.since_uptime:
                    stats[host][metric_type] = bean[key] / uptime
                else:
                    if key not in last[host]:
                        self.first_iteration = 1
                    else:
                        stats[host][metric_type] = (bean[key] - last[host][key]) / self.interval
                    last[host][key] = bean[key]

    def print_stats(self, host):
        stats = self.stats
        tstamp = time.strftime('%F %T')
        if not stats:
            print("No regionserver stats found. Did you specify correct regionserver addresses and --port?")
            sys.exit(1)
        if self.first_iteration:
            log.info('first iteration, skipping iteration until we have a differential')
            print('{}\t{} rate stats will be available in next iteration in {} sec{}'\
                  .format(tstamp, host, self.interval, plural(self.interval)))
            self.first_iteration = 0
            return
        for metric in self.request_types:
            if self.request_type and metric not in self.request_type:
                continue
            try:
                val = '{:8.0f}'.format(stats[host][metric])
            # might happen if server is down for maintenance - in which case N/A and retry later rather than crash
            except KeyError:
                val = 'N/A'
            print('{:20s}\t{:20s}\t{:10s}\t{}'\
                  .format(tstamp, host, metric, val))
        print()

    # some extra effort to make it look the same as HBase presents it as
    #def encode_char(self, char):
    #    if char in string.printable and char not in ('\t', '\n', '\r', '\x0b', '\x0c'):
    #        return char
    #    _ = '{0:#0{1}x}'.format(ord(char), 4).replace('0x', '\\x')
    #    _ = self.re_hex.sub(lambda x: x.group(1).upper(), _)
    #    return _


if __name__ == '__main__':
    HBaseRegionServerRequests().main()
