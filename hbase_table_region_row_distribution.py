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

Tool to show distribution of rows across HBase table regions via Thrift API

Designed to help analyze region hotspotting caused by row key skew while lab testing
small to medium data distributions and is not scalable due to being a very heavy
region-by-region full table scan operation ie. O(n). Tested with 50M data points.

This may time out on HBase tables with very large regions such as wide row opentsdb tables,
in which case you should instead consider using Spark, Hive or Phoenix instead.

Tested on Hortonworks HDP 2.5 (HBase 1.1.2) and Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2, 1.3.1

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

#import logging
import os
import sys
import traceback
import numpy as np
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, log_option, die, code_error, support_msg_api, autoflush
    from hbase_show_table_region_ranges import HBaseShowTableRegionRanges
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.2'


class HBaseTableRegionRowDistribution(HBaseShowTableRegionRanges):

    def __init__(self):
        # Python 2.x
        super(HBaseTableRegionRowDistribution, self).__init__()
        # Python 3.x
        # super().__init__()
        self.timeout_default = 6 * 3600
        self._regions_meta = []
        self.no_region_col = False
        self.sort = None
        self.sort_desc = False
        self.valid_sorts = ('count', 'server')
        self.total_rows = 0
        self.row_count_header = 'Row Count'
        self.row_count_width = len(self.row_count_header)
        self.row_count_pc_header = '% of Total Rows'
        self.row_count_pc_width = len(self.row_count_pc_header)
        autoflush()

    def add_options(self):
        super(HBaseTableRegionRowDistribution, self).add_options()
        self.add_opt('-n', '--no-region-name', action='store_true',
                     help='Do not output Region name column to save screen space')
        self.add_opt('-s', '--sort', metavar='|'.join(self.valid_sorts),
                     help='Sort ordering (possible values: count, server)' +
                     '. Makes it easier to see the regions with the most rows or if one server is rows heavy regions' +
                     '. See also hbase_calculate_server_row_distribution.py')
        self.add_opt('-d', '--desc', action='store_true', help='Reverse sort order (descending)')

    def local_main(self, table_conn):
        self.no_region_col = self.get_opt('no_region_name')
        self.sort = self.get_opt('sort')
        self.sort_desc = self.get_opt('desc')
        if self.sort is not None:
            self.sort = self.sort.lower()
            if self.sort not in self.valid_sorts:
                self.usage('invalid --sort option given, must be one of: {0}'.format(', '.join(self.valid_sorts)))
        log_option('no region name', self.no_region_col)
        log_option('sort', self.sort)
        if self.no_region_col:
            self.total_width -= self.region_width
        num_regions = len(self._regions)
        # sanity check and protect against division by zero in summary stats
        if num_regions < 1:
            die('number of regions detected = {0:d} (< 1)'.format(num_regions))
        self.populate_region_metadata()
        self.calculate_widths()
        self.populate_row_counts(table_conn)
        self.calculate_row_count_widths()
        self.calculate_row_percentages()
        self.print_table_region_row_counts()
        self.print_summary()

    def populate_region_metadata(self):
        log.info('getting region metadata')
        try:
            for region in self._regions:
                self._regions_meta.append({
                    'name': self.bytes_to_str(self.shorten_region_name(region['name'])),
                    'start_key': self.bytes_to_str(region['start_key']),
                    'end_key': self.bytes_to_str(region['end_key']),
                    'server': '{0}:{1}'.format(region['server_name'], region['port'])
                })
        except KeyError as _:
            die('error parsing region info: {0}. '.format(_) + support_msg_api())

    def populate_row_counts(self, table_conn):
        if not self.conn.is_table_enabled(self.table):
            die("table '{0}' is not enabled".format(self.table))
        log.info('getting region row counts')
        if self.verbose < 2:
            print('progress dots (1 per region scanned): ', file=sys.stderr, end='')
        for region in self._regions_meta:
            log.info("scanning region '%s'", region['name'])
            region['row_count'] = self.scan_count(table_conn,
                                                  region['start_key'],
                                                  region['end_key'])
            if self.verbose < 2:
                print('.', file=sys.stderr, end='')
        if self.verbose < 2:
            print(file=sys.stderr)

    @staticmethod
    def scan_count(table_conn, start_row, end_row):
        # row_stop is exclusive but so is end_row passed from region info so shouldn't be off by one
        rows = table_conn.scan(row_start=start_row, row_stop=end_row, columns=[])
        # memory vs time trade off
        #return len(list(rows))
        return sum(1 for _ in rows)

    def calculate_row_count_widths(self):
        for region in self._regions_meta:
            _ = len(str(region['row_count']))
            if _ > self.row_count_width:
                self.row_count_width = _
        self.total_width += self.row_count_width + self.row_count_pc_width + len(self.separator) * 2

    def calculate_row_percentages(self):
        log.info('calculating row percentages')
        for region in self._regions_meta:
            self.total_rows += region['row_count']
        if not self._regions_meta:
            die("no regions found for table '{0}'!".format(self.table))
        # make sure we don't run in to division by zero error
        if self.total_rows == 0:
            die("0 total rows detected for table '{0}'!".format(self.table))
        if self.total_rows < 0:
            die("negative total rows detected for table '{0}'!".format(self.table))
        for region in self._regions_meta:
            region['pc'] = '{0:.2f}'.format(region['row_count'] / max(self.total_rows, 1) * 100)

    def print_table_region_row_counts(self):
        if self.sort:
            if self.sort == 'count':
                log.info('sorting output by counts')
                if self.sort_desc:
                    self._regions_meta.sort(key=lambda _: -_['row_count'])
                else:
                    self._regions_meta.sort(key=lambda _: _['row_count'])
            elif self.sort == 'server':
                log.info('sorting output by server')
                self._regions_meta.sort(key=lambda _: _['server'])
                if self.sort_desc:
                    self._regions_meta.reverse()
            else:
                code_error('--sort was not either count or server')
        print('=' * self.total_width)
        if not self.no_region_col:
            print('{0:{1}}{2}'.format(self.region_header,
                                      self.region_width,
                                      self.separator),
                  end='')
        print('{0:{1}}{2}'.format(self.start_key_header,
                                  self.start_key_width,
                                  self.separator),
              end='')
        print('{0:{1}}{2}'.format(self.end_key_header,
                                  self.end_key_width,
                                  self.separator),
              end='')
        print('{0:{1}}{2}'.format(self.server_header,
                                  self.server_width,
                                  self.separator),
              end='')
        print('{0:{1}}{2}{3}'.format(self.row_count_header,
                                     self.row_count_width,
                                     self.separator,
                                     self.row_count_pc_header)
             )
        print('=' * self.total_width)
        for region in self._regions_meta:
            if not self.no_region_col:
                print('{0:{1}}{2}'.format(region['name'],
                                          self.region_width,
                                          self.separator),
                      end='')
            print('{0:{1}}{2}'.format(region['start_key'],
                                      self.start_key_width,
                                      self.separator),
                  end='')
            print('{0:{1}}{2}'.format(region['end_key'],
                                      self.end_key_width,
                                      self.separator),
                  end='')
            print('{0:{1}}{2}'.format(region['server'], self.server_width, self.separator), end='')
            print('{0:{1}}{2}{3:>10}'.format(region['row_count'],
                                             self.row_count_width,
                                             self.separator,
                                             region['pc']))

    def print_summary(self):
        num_regions = len(self._regions)
        regions_meta_non_zero = [region for region in self._regions_meta if region['row_count'] > 0]
        num_regions_non_zero = len(regions_meta_non_zero)
        np_rows = np.array([int(region['row_count']) for region in self._regions_meta])
        avg_rows = np_rows.mean()
        (first_quartile, median, third_quartile) = np.percentile(np_rows, [25, 50, 75]) # pylint: disable=no-member
        print()
        print('Total Rows: {0:d}'.format(self.total_rows))
        print('Total Regions: {0:d}'.format(num_regions))
        print('Empty Regions: {0:d}'.format(num_regions - num_regions_non_zero))
        print('Used  Regions: {0:d}'.format(num_regions_non_zero))
        print()
        print('Average Rows Per Region: {0:.2f} ({1:.2f}%)'.format(avg_rows, avg_rows / self.total_rows * 100))
        width = 0
        (first_quartile_non_empty, median_non_empty, third_quartile_non_empty) = (None, None, None)
        if regions_meta_non_zero:
            np_rows_non_empty = np.array([int(region['row_count']) for region in regions_meta_non_zero])
            avg_rows_non_empty = np_rows_non_empty.mean()
            (first_quartile_non_empty, median_non_empty, third_quartile_non_empty) = \
                np.percentile(np_rows_non_empty, [25, 50, 75]) # pylint: disable=no-member
        for stat in (first_quartile, median, third_quartile,
                     first_quartile_non_empty, median_non_empty, third_quartile_non_empty):
            _ = len(str(stat))
            if _ > width:
                width = _
        print()
        print('Rows per Region:')
        print('1st quartile:  {0:{1}} ({2:.2f}%)'.format(first_quartile, width, first_quartile / self.total_rows * 100))
        print('median:        {0:{1}} ({2:.2f}%)'.format(median, width, median / self.total_rows * 100))
        print('3rd quartile:  {0:{1}} ({2:.2f}%)'.format(third_quartile, width, third_quartile / self.total_rows * 100))
        if regions_meta_non_zero:
            print()
            print('Excluding Empty Regions:\n')
            print('Average Rows Per Region: {0:.2f} ({1:.2f}%)'.format(avg_rows_non_empty,
                                                                       avg_rows_non_empty / self.total_rows * 100))
            print()
            print('Rows per Region:')
            print('1st quartile:  {0:{1}} ({2:.2f}%)'.format(first_quartile_non_empty, width,
                                                             first_quartile_non_empty / self.total_rows * 100))
            print('median:        {0:{1}} ({2:.2f}%)'.format(median_non_empty, width,
                                                             median_non_empty / self.total_rows * 100))
            print('3rd quartile:  {0:{1}} ({2:.2f}%)'.format(third_quartile_non_empty, width,
                                                             third_quartile_non_empty  / self.total_rows * 100))
        print()


if __name__ == '__main__':
    HBaseTableRegionRowDistribution().main()
