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

Tool to find biggest or smallest least used HBase Regions across any given RegionServers using JMX API stats

Designed to find the biggest and smallest hbase regions to look at migrating for storage skew across RegionServers

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
import traceback
import requests
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import validate_host, validate_port, validate_chars, validate_int
    from harisekhon.utils import UnknownError, CriticalError, printerr, log
    from harisekhon import CLI, RequestHandler
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.5.1'


class HBaseRegionsLeastUsed(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseRegionsLeastUsed, self).__init__()
        # Python 3.x
        # super().__init__()
        self.host_list = []
        self.port = 16030
        self.table = None
        self.namespace = 'default'
        self.stats = {}
        self.request_threshold = None
        self.regions_under_count = {}
        self.top_n = None
        self.count = 0
        self.timeout_default = 300
        self.url = None

    def add_options(self):
        self.add_opt('-P', '--port', default=os.getenv('HBASE_REGIONSERVER_PORT', self.port),
                     help='HBase RegionServer port (default: {})'.format(self.port))
        self.add_opt('-T', '--table', help='Table name (optional, returns regions for all tables otherwise)')
        self.add_opt('-N', '--namespace', default=self.namespace, help='Namespace (default: {})'.format(self.namespace))
        self.add_opt('-n', '--human', action='store_true', help='Humanize size metrics to KB, MB, GB etc')
        self.add_opt('-o', '--top', metavar='N', default=100, help='Only output regions with the top N sizes ' + \
                                                                   '(default: 100, may return more regions ' + \
                                                                   'than N if multiple have the same size)')
        self.add_opt('-r', '--requests', help='Only output regions with totalRequestCounts less than or equal to this')
        self.add_opt('-s', '--smallest', action='store_true', help='Sort by smallest (default: largest)')

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
        self.top_n = self.get_opt('top')
        if self.top_n:
            validate_int(self.top_n, 'top N', 1)
            self.top_n = int(self.top_n)
        self.request_threshold = self.get_opt('requests')
        validate_int(self.request_threshold, 'request count threshold')
        self.request_threshold = int(self.request_threshold)

    def run(self):
        for host in self.host_list:
            url = 'http://{host}:{port}/jmx'.format(host=host, port=self.port)
            url += '?qry=Hadoop:service=HBase,name=RegionServer,sub=Regions'
            try:
                self.run_host(host, url)
            except (CriticalError, UnknownError, requests.RequestException) as _:
                printerr("ERROR querying JMX stats for host '{}': {}".format(host, _), )

    def run_host(self, host, url):
        log.info('querying %s', host)
        req = RequestHandler().get(url)
        json_data = json.loads(req.text)
        beans = json_data['beans']
        for bean in beans:
            log.debug('processing Regions bean')
            if bean['name'] == 'Hadoop:service=HBase,name=RegionServer,sub=Regions':
                self.process_bean(host, bean)
                self.print_stats(host)

    def process_bean(self, host, bean):
        prefix = '^Namespace_{namespace}_table_({table})_region_(.+)_metric_'\
                                  .format(namespace=self.namespace, table=self.table)
        region_regex = re.compile('{}storeFileSize'.format(prefix))
        request_count_regex = re.compile('{}(read|write)RequestCount'.format(prefix))
        stats = self.stats
        regions_under_count = self.regions_under_count
        region_counts = {}
        got_total = 0
        for key in bean:
            match = region_regex.match(key)
            if match:
                table = match.group(1)
                region = match.group(2)
                log.info('matched table %s region %s storeFileSize = %s', table, region, bean[key])
                size = bean[key]
                if size not in stats:
                    stats[size] = []
                stats[size].append((host, table, region))
                continue
            match2 = request_count_regex.match(key)
            if match2:
                table = match2.group(1)
                region = match2.group(2)
                request_type = match2.group(3)
                log.info('matched table %s region %s %sRequestCount = %s', table, region, request_type, bean[key])
                request_count = bean[key]
                if region not in region_counts:
                    region_counts[region] = 0
                    got_total = 0
                else:
                    got_total = 1
                # add read + write request counts
                region_counts[region] += request_count
                if got_total and region_counts[region] <= self.request_threshold:
                    regions_under_count[region] = region_counts[region]
                continue

    def print_stats(self, host):
        stats = self.stats
        regions_under_count = self.regions_under_count
        if not stats:
            print("No table regions found for table '{}'. Did you specify the correct table name?".format(self.table))
            sys.exit(1)
        size_list = sorted(stats)
        if not self.get_opt('smallest'):
            size_list = list(reversed(size_list))
        if self.top_n:
            size_list = size_list[0:self.top_n]
        human = self.get_opt('human')
        if human:
            import humanize
        for size in size_list:
            for _ in stats[size]:
                host2 = _[0]
                if host != host2:
                    continue
                table = _[1]
                region = _[2]
                if region not in regions_under_count:
                    continue
                self.count += 1
                if self.count > self.top_n:
                    sys.exit(0)
                size_human = size
                if human:
                    size_human = humanize.naturalsize(size_human)
                print('{:20s}\t{:20s}\t{:20s}\t{:10}\t{}'\
                      .format(host, table, region, size_human, regions_under_count[region]))
        print()

    # some extra effort to make it look the same as HBase presents it as
    #def encode_char(self, char):
    #    if char in string.printable and char not in ('\t', '\n', '\r', '\x0b', '\x0c'):
    #        return char
    #    _ = '{0:#0{1}x}'.format(ord(char), 4).replace('0x', '\\x')
    #    _ = self.re_hex.sub(lambda x: x.group(1).upper(), _)
    #    return _


if __name__ == '__main__':
    HBaseRegionsLeastUsed().main()
