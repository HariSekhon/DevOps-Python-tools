#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-08 09:02:01 +0100 (Sat, 08 Oct 2016)
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

Tool to show distribution of HBase row keys by configurable prefix lengths for a table via Thrift API

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
import re
import socket
import string
import sys
import traceback
try:
    # pylint: disable=wrong-import-position
    import numpy as np
    import happybase  # pylint: disable=unused-import
    # happybase.hbase.ttypes.IOError no longer there in Happybase 1.0
    try:
        # this is only importable after happybase module
        # pylint: disable=import-error
        from Hbase_thrift import IOError as HBaseIOError
    except ImportError:
        # probably Happybase <= 0.9
        # pylint: disable=import-error,no-name-in-module,ungrouped-imports
        from happybase.hbase.ttypes import IOError as HBaseIOError
    from thriftpy.thrift import TException as ThriftException
except ImportError as _:
    print('module import error - did you forget to build this project?\n\n'
          + traceback.format_exc(), end='')
    sys.exit(4)
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, die, autoflush, merge_dicts #, support_msg_api
    from harisekhon.utils import validate_host, validate_port, validate_chars, validate_int
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.2'


class HBaseTableRegionRowDistribution(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseTableRegionRowDistribution, self).__init__()
        # Python 3.x
        # super().__init__()
        self.conn = None
        self.host = None
        self.port = 9090
        self.table = None
        self.timeout_default = 6 * 3600
        self.re_hex = re.compile('([a-f]+)') # to convert to uppercase later for aesthetics
        self.total_rows = 0
        self.rows = {}
        self.sort = False
        self.sort_desc = False
        self.prefix_length = 1
        self.key_prefix_header = 'Key Prefix'
        self.key_prefix_width = len(self.key_prefix_header)
        self.row_count_header = 'Row Count'
        self.row_count_width = len(self.row_count_header)
        self.row_count_pc_header = '% of Total Rows'
        self.row_count_pc_width = len(self.row_count_pc_header)
        self.separator = '    '
        self.total_width = (self.key_prefix_width +
                            self.row_count_width +
                            self.row_count_pc_width +
                            len(self.separator) * 2)
        autoflush()

    def add_options(self):
        self.add_hostoption(name='HBase Thrift Server', default_host='localhost', default_port=self.port)
        self.add_opt('-T', '--table', help='Table name')
        self.add_opt('-K', '--key-prefix-length', metavar='<int>', default=self.prefix_length,
                     help='Row key prefix summary length (default: {0})'.format(self.prefix_length) +
                     '. Use with increasing sizes for more granular analysis')
        self.add_opt('-s', '--sort', action='store_true', help='Sort by row count')
        self.add_opt('-d', '--desc', action='store_true', help='Descending sort order')
        self.add_opt('-l', '--list-tables', action='store_true', help='List tables and exit')

    def process_args(self):
        #log.setLevel(logging.INFO)
        self.no_args()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        self.table = self.get_opt('table')
        self.prefix_length = self.get_opt('key_prefix_length')
        self.sort = self.get_opt('sort')
        self.sort_desc = self.get_opt('desc')
        validate_host(self.host)
        validate_port(self.port)
        # happybase socket requires an integer
        self.port = int(self.port)
        if not self.get_opt('list_tables'):
            validate_chars(self.table, 'hbase table', 'A-Za-z0-9:._-')
            validate_int(self.prefix_length, 'row key prefix length', 1, 10)
            self.prefix_length = int(self.prefix_length)

    def get_tables(self):
        try:
            return self.conn.tables()
        except (socket.timeout, ThriftException, HBaseIOError) as _:
            die('ERROR while trying to get table list: {0}'.format(_))

    def run(self):
        # might have to use compat / transport / protocol args for older versions of HBase or if protocol has been
        # configured to be non-default, see:
        # http://happybase.readthedocs.io/en/stable/api.html#connection
        try:
            log.info('connecting to HBase Thrift Server at %s:%s', self.host, self.port)
            self.conn = happybase.Connection(host=self.host, port=self.port, timeout=10 * 1000)  # ms
            tables = self.get_tables()
            if self.get_opt('list_tables'):
                print('Tables:\n\n' + '\n'.join(tables))
                sys.exit(3)
            if self.table not in tables:
                die("HBase table '{0}' does not exist!".format(self.table))
            table_conn = self.conn.table(self.table)
            self.populate_row_counts(table_conn)
            self.calculate_row_count_widths()
            self.calculate_row_percentages()
            self.print_table_row_prefix_counts()
            self.print_summary()
            log.info('finished, closing connection')
            self.conn.close()
        except (socket.timeout, ThriftException, HBaseIOError) as _:
            die('ERROR: {0}'.format(_))

    def populate_row_counts(self, table_conn):
        if not self.conn.is_table_enabled(self.table):
            die("table '{0}' is not enabled".format(self.table))
        log.info('getting row counts (this may take a long time)')
        #rows = table_conn.scan(columns=[])
        rows = table_conn.scan() # columns=[]) doesn't return without cf
        if self.verbose < 2:
            print('progress dots (one per 10,000 rows): ', file=sys.stderr, end='')
        for row in rows:
            #log.debug(row)
            key = row[0]
            prefix = key[0:min(self.prefix_length, len(key))]
            prefix = self.bytes_to_str(prefix)
            if not self.rows.get(prefix):
                self.rows[prefix] = {'row_count': 0}
            self.rows[prefix]['row_count'] += 1
            self.total_rows += 1
            if self.verbose < 2 and self.total_rows % 10000 == 0:
                print('.', file=sys.stderr, end='')
        if self.verbose < 2:
            print(file=sys.stderr)

    def bytes_to_str(self, arg):
        # unfortunately this is passed in a type str, must encode char by char
        #if isStr(arg):
        #    return arg
        #elif isByte(arg):
        #else:
        #    die('unrecognized region name/start/end key, not bytes or string!')
        encode_char = self.encode_char
        return ''.join([encode_char(x) for x in arg])

    # some extra effort to make it look the same as HBase presents it as
    def encode_char(self, char):
        if char in string.printable and char not in ('\t', '\n', '\r', '\x0b', '\x0c'):
            return char
        _ = '{0:#0{1}x}'.format(ord(char), 4).replace('0x', '\\x')
        _ = self.re_hex.sub(lambda x: x.group(1).upper(), _)
        return _

    def calculate_row_count_widths(self):
        for row_prefix in self.rows:
            _ = len(row_prefix)
            if _ > self.key_prefix_width:
                self.key_prefix_width = _
            _ = len(str(self.rows[row_prefix]['row_count']))
            if _ > self.row_count_width:
                self.row_count_width = _
        self.total_width = (self.key_prefix_width +
                            self.row_count_width +
                            self.row_count_pc_width +
                            len(self.separator) * 2)

    def calculate_row_percentages(self):
        log.info('calculating row percentages')
        # incremented instead now for one progress dot per 10k lines
        #for row_prefix in self.rows:
        #    self.total_rows += self.rows[row_prefix]['row_count']
        # make sure we don't run in to division by zero error
        if self.total_rows == 0:
            die("0 total rows detected for table '{0}'!".format(self.table))
        if self.total_rows < 0:
            die("negative total rows detected for table '{0}'!".format(self.table))
        for row_prefix in self.rows:
            self.rows[row_prefix]['pc'] = '{0:.2f}'.format(self.rows[row_prefix]['row_count'] /
                                                           max(self.total_rows, 1) * 100)

    def print_table_row_prefix_counts(self):
        print('=' * self.total_width)
        print('{0:{1}}{2}'.format(self.key_prefix_header,
                                  self.key_prefix_width,
                                  self.separator),
              end='')
        print('{0:{1}}{2}{3}'.format(self.row_count_header,
                                     self.row_count_width,
                                     self.separator,
                                     self.row_count_pc_header)
             )
        print('=' * self.total_width)
        tmp_list = [merge_dicts({'key_prefix': key}, self.rows[key]) for key in self.rows]
        if self.sort:
            if self.sort_desc:
                tmp_list.sort(key=lambda _: -_['row_count'])
            else:
                tmp_list.sort(key=lambda _: _['row_count'])
        for item in tmp_list:
            print('{0:{1}}{2}'.format(item['key_prefix'],
                                      self.key_prefix_width,
                                      self.separator),
                  end='')
            print('{0:{1}}{2}{3:>10}'.format(item['row_count'],
                                             self.row_count_width,
                                             self.separator,
                                             item['pc']))

    def print_summary(self):
        np_rows = np.array([int(self.rows[row]['row_count']) for row in self.rows])
        avg_rows = np_rows.mean()
        (first_quartile, median, third_quartile) = np.percentile(np_rows, [25, 50, 75]) # pylint: disable=no-member
        print()
        print('Total Rows: {0:d}'.format(self.total_rows))
        print('Unique Row Key Prefixes (length \'{0}\'): {1}'.format(self.prefix_length, len(self.rows)))
        print('Average Rows Per Prefix: {0:.2f} ({1:.2f}%)'.format(avg_rows, avg_rows / self.total_rows * 100))
        width = 0
        for stat in (first_quartile, median, third_quartile):
            _ = len(str(stat))
            if _ > width:
                width = _
        print()
        print('Rows per Prefix:')
        print('1st quartile:  {0:{1}} ({2:.2f}%)'.format(first_quartile, width, first_quartile / self.total_rows * 100))
        print('median:        {0:{1}} ({2:.2f}%)'.format(median, width, median / self.total_rows * 100))
        print('3rd quartile:  {0:{1}} ({2:.2f}%)'.format(third_quartile, width, third_quartile / self.total_rows * 100))
        print()


if __name__ == '__main__':
    HBaseTableRegionRowDistribution().main()
