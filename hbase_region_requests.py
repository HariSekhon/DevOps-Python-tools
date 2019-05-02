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

Tool to calculate HBase Region Requests Per Second or Average Since Startup using JMX API stats

Designed to help analyze region hotspotting (see also hbase_regionserver_request.py for regionserver load skew)

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
    from harisekhon.utils import validate_host, validate_port, validate_chars, validate_int
    from harisekhon.utils import UnknownError, CriticalError, support_msg_api, printerr, plural, log
    from harisekhon import CLI, RequestHandler
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.5.3'


class HBaseRegionsRequests(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseRegionsRequests, self).__init__()
        # Python 3.x
        # super().__init__()
        self.host_list = []
        self.port = 16030
        self.table = None
        self.namespace = 'default'
        self.interval = 1
        self.count = 0
        self.since_uptime = False
        self.show = set()
        self.stats = {}
        self.last = {}
        self.first_iteration = 0
        self.timeout_default = 300
        self.url = None
        self._regions = None

    def add_options(self):
        self.add_opt('-P', '--port', default=os.getenv('HBASE_REGIONSERVER_PORT', self.port),
                     help='HBase RegionServer port (default: {})'.format(self.port))
        self.add_opt('-T', '--table', help='Table name (optional, returns regions for all tables otherwise)')
        self.add_opt('-N', '--namespace', default=self.namespace, help='Namespace (default: {})'.format(self.namespace))
        self.add_opt('-i', '--interval', default=self.interval,
                     help='Interval to print rates at (default: {})'.format(self.interval))
        self.add_opt('-c', '--count', default=self.count,
                     help='Number of times to print stats (default: {}, zero means infinite)'.format(self.count))
        self.add_opt('-a', '--average', action='store_true', help='Calculate average since RegionServer startup')
        self.add_opt('--reads', action='store_true', help='Show read requests (default shows read and write)')
        self.add_opt('--writes', action='store_true', help='Show write requests (default shows read and write')
        self.add_opt('--total', action='store_true', help='Show total requests (default shows read and write)')
        self.add_opt('--skip-zeros', action='store_true', help="Don't output regions which have zero requests")

    def process_args(self):
        self.host_list = self.args
        if not self.host_list:
            self.usage('no host arguments given, must give at least one regionserver host as an argument')
        for host in self.host_list:
            validate_host(host)
        self.port = self.get_opt('port')
        validate_port(self.port)

        self.table = self.get_opt('table')
        table_chars = 'A-Za-z0-9:._-'
        if self.table:
            validate_chars(self.table, 'table', table_chars)
        else:
            self.table = '[{}]+'.format(table_chars)
        self.namespace = self.get_opt('namespace')
        validate_chars(self.namespace, 'hbase namespace', 'A-Za-z0-9:._-')
        self.interval = self.get_opt('interval')
        self.count = self.get_opt('count')
        self.since_uptime = self.get_opt('average')
        validate_int(self.interval, 'interval')
        validate_int(self.count, 'count')
        self.interval = int(self.interval)
        self.count = int(self.count)
        if self.count == 0:
            self.disable_timeout()
        if self.get_opt('reads'):
            self.show.add('read')
        if self.get_opt('writes'):
            self.show.add('write')
        if self.get_opt('total'):
            self.show.add('total')

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
                url += '?qry=Hadoop:service=HBase,name=RegionServer,sub=Regions'
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
            if bean['name'] == 'Hadoop:service=HBase,name=RegionServer,sub=Regions':
                self.process_bean(host, bean, uptime)
                self.print_stats(host)

    def process_bean(self, host, bean, uptime):
        region_regex = re.compile('^Namespace_{namespace}_table_({table})_region_(.+)_metric_(.+)RequestCount'\
                                  .format(namespace=self.namespace, table=self.table))
        stats = self.stats
        last = self.last
        for key in bean:
            match = region_regex.match(key)
            if match:
                table = match.group(1)
                region = match.group(2)
                metric_type = match.group(3)
                log.info('matched table %s region %s %s request count = %s', table, region, metric_type, bean[key])
                if host not in stats:
                    stats[host] = {}
                if host not in last:
                    last[host] = {}
                if table not in stats[host]:
                    stats[host][table] = {}
                if region not in stats[host][table]:
                    stats[host][table][region] = {}
                if self.since_uptime:
                    stats[host][table][region][metric_type] = bean[key] / uptime
                else:
                    # this isn't perfect - will result on a region split as well as first run
                    # but it's generally good enough
                    if key not in last[host]:
                        self.first_iteration = 1
                    else:
                        stats[host][table][region][metric_type] = (bean[key] - last[host][key]) / self.interval
                    last[host][key] = bean[key]
                # totalRequestCount field seems to not always be found, causing key errors later in print_stats()
                #
                # worse is that totalRequestCount calculation is wrong due to change
                #
                # See https://issues.apache.org/jira/browse/HBASE-20626
                #
                # which counts multi-requests as a single request, breaking the seemingly reasonable assertion
                #
                # assert readRequestCount + writeRequestcount == totalRequestCount
                #
                if 'read' in stats[host][table][region] and 'write' in stats[host][table][region]:
                    #log.debug('calculating total now we have read and write info')
                    stats[host][table][region]['total'] = stats[host][table][region]['read'] + \
                                                          stats[host][table][region]['write']

    def print_stats(self, host):
        stats = self.stats
        show = self.show
        skip_zeros = self.get_opt('skip_zeros')
        tstamp = time.strftime('%F %T')
        if not stats:
            print("No table regions found for table '{}'. Did you specify the correct table name?".format(self.table))
            sys.exit(1)
        if self.first_iteration:
            log.info('first iteration or recent new region, skipping iteration until we have a differential')
            print('{}\t{} rate stats will be available in next iteration in {} sec{}'\
                  .format(tstamp, host, self.interval, plural(self.interval)))
            self.first_iteration = 0
            return
        count = 0
        for table in sorted(stats[host]):
            for region in sorted(stats[host][table]):
                table_region = region
                if len(stats) > 1:
                    table_region = '{}:{}'.format(table, region)
                # maintain explicit order for humans
                # rather than iterate keys of region which will some out in the wrong order
                for metric in ('read', 'write', 'total'):
                    value = stats[host][table][region][metric]
                    if skip_zeros and int(value) == 0:
                        continue
                    if show and metric not in show:
                        continue
                    print('{:20s}\t{:20s}\t{:40s}\t{:10s}\t{:8.0f}'\
                          .format(tstamp, host, table_region, metric, value))
                    count += 1
        if count:
            print()

    # some extra effort to make it look the same as HBase presents it as
    #def encode_char(self, char):
    #    if char in string.printable and char not in ('\t', '\n', '\r', '\x0b', '\x0c'):
    #        return char
    #    _ = '{0:#0{1}x}'.format(ord(char), 4).replace('0x', '\\x')
    #    _ = self.re_hex.sub(lambda x: x.group(1).upper(), _)
    #    return _


if __name__ == '__main__':
    HBaseRegionsRequests().main()
