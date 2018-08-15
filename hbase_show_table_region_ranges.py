#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-05 13:57:37 +0100 (Wed, 05 Oct 2016)
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

Tool to show HBase table region ranges

Useful for exploring tables when evaluating pre-splitting strategies, eg. HexStringSplit vs UniformSplit vs Custom

See also:

- check_hbase_region_balance.py (in the Advanced Nagios Plugins Collection) to check the % imbalance on the
number of regions hosted across region servers to make sure there is a spread.
- hbase_calculate_table_region_row_distribution.py (in this DevOps Python Tools repo) to see the row distribution across regions
- hbase_calcualte_table_row_key_distribution.py (in this DevOps Python Tools repo) to see the row key distribution / data skew

Tested on Hortonworks HDP 2.5 (HBase 1.1.2) and Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2, 1.3.1

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

#import logging
import os
import re
import sys
import traceback
import socket
import string
try:
    # pylint: disable=wrong-import-position
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
    print('Happybase / thrift module import error - did you forget to build this project?\n\n'
          + traceback.format_exc(), end='')
    sys.exit(4)
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, log_option, die, support_msg_api
    from harisekhon.utils import validate_host, validate_port, validate_chars
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.5.1'


class HBaseShowTableRegionRanges(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseShowTableRegionRanges, self).__init__()
        # Python 3.x
        # super().__init__()
        self.conn = None
        self.host = None
        self.port = 9090
        self.table = None
        self.timeout_default = 300
        self.re_hex = re.compile('([a-f]+)') # to convert to uppercase later for aesthetics
        self.region_header = 'Region'
        self.start_key_header = 'Start Key'
        self.end_key_header = 'End Key'
        self.server_header = 'Server (host:port)'
        self.separator = '    '
        self.short_region_name = False
        self._regions = None
        self.region_width = len(self.region_header)
        self.start_key_width = len(self.start_key_header)
        self.end_key_width = len(self.end_key_header)
        self.server_width = len(self.server_header)
        self.total_width = (self.region_width + self.server_width +
                            self.start_key_width + self.end_key_width +
                            len(3 * self.separator))

    def add_options(self):
        self.add_hostoption(name='HBase Thrift Server', default_host='localhost', default_port=self.port)
        self.add_opt('-T', '--table', help='Table name')
        self.add_opt('-r', '--short-region-name', action='store_true',
                     help='Shorten region name to not include redundant table prefix')
        self.add_opt('-l', '--list-tables', action='store_true', help='List tables and exit')

    def process_args(self):
        #log.setLevel(logging.INFO)
        self.no_args()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        self.table = self.get_opt('table')
        validate_host(self.host)
        validate_port(self.port)
        # happybase socket requires an integer
        self.port = int(self.port)
        if not self.get_opt('list_tables'):
            validate_chars(self.table, 'hbase table', 'A-Za-z0-9:._-')
        self.short_region_name = self.get_opt('short_region_name')
        log_option('shorten region name', self.short_region_name)

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
            self._regions = table_conn.regions()
            self.local_main(table_conn)
            log.info('finished, closing connection')
            self.conn.close()
        except (socket.timeout, ThriftException, HBaseIOError) as _:
            die('ERROR: {0}'.format(_))

    # table_conn is used in inherited in hbase_calculate_table_region_row_distribution.py
    def local_main(self, table_conn):  # pylint: disable=unused-argument
        self.calculate_widths()
        self.print_table_regions()

    def calculate_widths(self):
        try:
            for region in self._regions:
                log.debug(region)
                _ = len(self.bytes_to_str(self.shorten_region_name(region['name'])))
                if _ > self.region_width:
                    self.region_width = _
                _ = len(self.bytes_to_str(region['start_key']))
                if _ > self.start_key_width:
                    self.start_key_width = _
                _ = len(self.bytes_to_str(region['end_key']))
                if _ > self.end_key_width:
                    self.end_key_width = _
                _ = len(region['server_name'] + ':' + str(region['port']))
                if _ > self.server_width:
                    self.server_width = _
        except KeyError as _:
            die('error parsing region info: {0}. '.format(_) + support_msg_api())
        self.total_width = (self.region_width + self.server_width +
                            self.start_key_width + self.end_key_width +
                            len(3 * self.separator))

    def shorten_region_name(self, region_name):
        if self.short_region_name:
            return region_name.lstrip(self.table + ',')
        return region_name

    # some extra effort to make it look the same as HBase presents it as
    def encode_char(self, char):
        if char in string.printable and char not in ('\t', '\n', '\r', '\x0b', '\x0c'):
            return char
        _ = '{0:#0{1}x}'.format(ord(char), 4).replace('0x', '\\x')
        _ = self.re_hex.sub(lambda x: x.group(1).upper(), _)
        return _

    def bytes_to_str(self, arg):
        # unfortunately this is passed in a type str, must encode char by char
        #if isStr(arg):
        #    return arg
        #elif isByte(arg):
        #else:
        #    die('unrecognized region name/start/end key, not bytes or string!')
        encode_char = self.encode_char
        return ''.join([encode_char(x) for x in arg])

    def print_table_regions(self):
        print('=' * self.total_width)
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
        print('{0}'.format(self.server_header))
        print('=' * self.total_width)
        try:
            for region in self._regions:
                print('{0:{1}}{2}'.format(self.bytes_to_str(self.shorten_region_name(region['name'])),
                                          self.region_width,
                                          self.separator),
                      end='')
                print('{0:{1}}{2}'.format(self.bytes_to_str(region['start_key']),
                                          self.start_key_width,
                                          self.separator),
                      end='')
                print('{0:{1}}{2}'.format(self.bytes_to_str(region['end_key']),
                                          self.end_key_width,
                                          self.separator),
                      end='')
                print('{0}:{1}'.format(region['server_name'], region['port']))
        except KeyError as _:
            die('error parsing region info: {0}. '.format(_) + support_msg_api())
        print('\nNumber of Regions: {0:d}'.format(len(self._regions)))
        # old method
#        log.info('getting hbase:meta table instance')
#        table = self.conn.table('hbase:meta')
#        log.info('scanning hbase:meta')
#        scanner = table.scan(row_prefix=self.table, columns=('info:regioninfo', 'info:server'), sorted_columns=False)
#        self.start_key_width = 20
#        self.end_key_width = 20
#        for row in scanner:
#            log.debug('Raw RegionInfo: %s', row)
#            if len(row) != 2:
#                die('UNKNOWN: row len != 2, please use --debug to see raw info to deduce why this is. '
#                    + support_msg_api())
#            key = row[0]
#            cf = row[1] # pylint: disable=invalid-name
#            print(key, end='\t')
#            # todo: decode regioninfo
#            regioninfo = cf['info:regioninfo']
#            regioninfo = unicode(regioninfo, errors='ignore')
#            regioninfo = bytes(regioninfo).decode('utf-8')
#            regioninfo = regioninfo.replace('\n', '')
#            regioninfo = filter(lambda x: x in set(string.ascii_letters + string.digits), regioninfo)
#            print('{regioninfo:{width}}'.format(regioninfo=regioninfo,
#                                                width=self.start_key_width + self.end_key_width + 4), end='\t')
#            print(cf['info:server'])


if __name__ == '__main__':
    HBaseShowTableRegionRanges().main()
