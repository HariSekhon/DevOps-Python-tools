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

Tool to find the biggest or smallest HBase Regions across any given RegionServers using JMX API stats

Designed to find big and small regions to look at migrating for storage skew across RegionServers

Argument list should be one or more RegionServers to dump the JMX stats from

See also hbase_regions_by_memstore_size.py
         hbase_regions_least_used.py

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
__version__ = '0.6.2'


class HBaseRegionsBySize(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseRegionsBySize, self).__init__()
        # Python 3.x
        # super().__init__()
        self.host_list = []
        self.port = 16030
        self.table = None
        self.namespace = 'default'
        self.metric = 'storeFileSize'
        self.region_regex = None
        self.stats = {}
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
        self.add_opt('-o', '--top', default=100, help='Only output regions with the top N sizes ' + \
                                                      '(default: 100, may return more regions ' + \
                                                      'than N if multiple have the same size)')
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
        self.region_regex = re.compile('^Namespace_{namespace}_table_({table})_region_(.+)_metric_{metric}'\
                                       .format(namespace=self.namespace, table=self.table, metric=self.metric))
        self.top_n = self.get_opt('top')
        if self.top_n:
            validate_int(self.top_n, 'top N', 1)
            self.top_n = int(self.top_n)

    def run(self):
        for host in self.host_list:
            url = 'http://{host}:{port}/jmx'.format(host=host, port=self.port)
            url += '?qry=Hadoop:service=HBase,name=RegionServer,sub=Regions'
            try:
                self.run_host(host, url)
            except (CriticalError, UnknownError, requests.RequestException) as _:
                printerr("ERROR querying JMX stats for host '{}': {}".format(host, _), )
        self.print_stats()

    def run_host(self, host, url):
        log.info('querying %s', host)
        req = RequestHandler().get(url)
        json_data = json.loads(req.text)
        beans = json_data['beans']
        for bean in beans:
            log.debug('processing Regions bean')
            if bean['name'] == 'Hadoop:service=HBase,name=RegionServer,sub=Regions':
                self.process_bean(host, bean)

    def process_bean(self, host, bean):
        region_regex = self.region_regex
        stats = self.stats
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

    def print_stats(self):
        stats = self.stats
        if not stats:
            print("No table regions found for table '{}'. Did you specify the correct table name?".format(self.table))
            sys.exit(1)
        size_list = sorted(stats)
        if not self.get_opt('smallest'):
            size_list = list(reversed(size_list))
        human = self.get_opt('human')
        if human:
            import humanize
        for size in size_list:
            for _ in stats[size]:
                if self.top_n and self.count > self.top_n:
                    sys.exit(0)
                self.count += 1
                host = _[0]
                table = _[1]
                region = _[2]
                size_human = size
                if human:
                    size_human = humanize.naturalsize(size_human)
                print('{:20s}\t{:20s}\t{:20s}\t{:>10}'\
                      .format(host, table, region, size_human))
        print()

    # some extra effort to make it look the same as HBase presents it as
    #def encode_char(self, char):
    #    if char in string.printable and char not in ('\t', '\n', '\r', '\x0b', '\x0c'):
    #        return char
    #    _ = '{0:#0{1}x}'.format(ord(char), 4).replace('0x', '\\x')
    #    _ = self.re_hex.sub(lambda x: x.group(1).upper(), _)
    #    return _


if __name__ == '__main__':
    HBaseRegionsBySize().main()
