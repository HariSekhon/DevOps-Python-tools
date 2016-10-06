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

Tool to show distribution of rows across HBase table regions to help analyze hotspotting caused by row key skew

This a very heavy operation and can takes a very long time to run for large tables as it runs a full table scan
region-by-region ie. O(n). Should be run periodically for analysis only.

Tested on Hortonworks HDP 2.5 (HBase 1.1.2) and Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

#import logging
import os
import sys
import traceback
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, die, support_msg_api, autoflush
    from hbase_show_table_region_ranges import HBaseShowTableRegionRanges
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2'


class HBaseShowTableRegionRowDistribution(HBaseShowTableRegionRanges):

    def __init__(self):
        # Python 2.x
        super(HBaseShowTableRegionRowDistribution, self).__init__()
        # Python 3.x
        # super().__init__()
        self.timeout_default = 6 * 3600
        self.regions = []
        self.no_region_col = False
        self.total_rows = 0
        self.row_count_header = 'Row Count'
        self.row_count_width = len(self.row_count_header)
        self.row_count_pc_header = '% of Total Rows'
        self.row_count_pc_width = len(self.row_count_pc_header)
        autoflush()

    def add_options(self):
        super(HBaseShowTableRegionRowDistribution, self).add_options()
        self.add_opt('-n', '--no-region-name', action='store_true',
                     help='Do not output Region name column to save screen space')

    def local_main(self, table_conn):
        self.calculate_widths(table_conn)
        self.no_region_col = self.get_opt('no_region_name')
        if self.no_region_col:
            self.total_width -= self.region_width
        self.populate_region_metadata(table_conn)
        self.populate_row_counts(table_conn)
        self.calculate_row_count_widths()
        self.calculate_row_percentages()
        self.print_table_region_row_counts()

    def calculate_row_count_widths(self):
        for region in self.regions:
            _ = len(str(region['row_count']))
            if _ > self.row_count_width:
                self.row_count_width = _
        self.total_width += self.row_count_width + self.row_count_pc_width + len(self.separator) * 2

    def calculate_row_percentages(self):
        log.info('calculating row percentages')
        for region in self.regions:
            self.total_rows += region['row_count']
        # make sure we don't run in to division by zero error
        #if self.total_rows == 0:
        #    die("0 total rows detected for table '{0}'!".format(self.table))
        if self.total_rows < 0:
            die("negative total rows detected for table '{0}'!".format(self.table))
        for region in self.regions:
            region['pc'] = '{0:.2f}'.format(region['row_count'] / max(self.total_rows, 1) * 100)

    def print_table_region_row_counts(self):
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
        for region in self.regions:
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

    def populate_region_metadata(self, table_conn):
        log.info('getting region metadata')
        try:
            for region in table_conn.regions():
                self.regions.append({
                    'name': self.bytes_to_str(self.shorten_region_name(region['name'])),
                    'start_key': self.bytes_to_str(region['start_key']),
                    'end_key': self.bytes_to_str(region['end_key']),
                    'server': '{0}:{1}'.format(region['server_name'], region['port'])
                })
        except KeyError as _:
            die('error parsing region info: {0}. '.format(_) + support_msg_api())

    def populate_row_counts(self, table_conn):
        log.info('getting region row counts')
        if self.verbose < 2:
            print('progress dots (1 per region scanned): ', end='')
        for region in self.regions:
            log.info("scanning region '%s'", region['name'])
            region['row_count'] = self.scan_count(table_conn,
                                                  region['start_key'],
                                                  region['end_key'])
            if self.verbose < 2:
                print('.', end='')
        if self.verbose < 2:
            print()

    @staticmethod
    def scan_count(table_conn, start_row, end_row):
        # row_stop is exclusive but so is end_row passed from region info so shouldn't be off by one
        rows = table_conn.scan(row_start=start_row, row_stop=end_row)
        return len(list(rows))


if __name__ == '__main__':
    HBaseShowTableRegionRowDistribution().main()
