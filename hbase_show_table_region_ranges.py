#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-05 13:57:37 +0100 (Wed, 05 Oct 2016)
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

Tool to show HBase table region ranges

Useful for exploring tables when evaluating pre-splitting strategies, eg. HexStringSplit vs UniformSplit

Tested on Hortonworks HDP 2.3 (HBase 1.1.2) and Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2

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
import happybase
from thriftpy.thrift import TException as ThriftException
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, die, support_msg_api
    from harisekhon.utils import validate_host, validate_port, validate_chars, isStr
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2'


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
        self.re_hex = re.compile('([a-f]+)')

    def add_options(self):
        self.add_hostoption(name='HBase Thrift Server', default_host='localhost', default_port=self.port)
        self.add_opt('-T', '--table', help='Table name')
        self.add_opt('-l', '--list-tables', action='store_true', help='List tables and exit')

    def process_args(self):
        #log.setLevel(logging.INFO)
        self.no_args()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        self.table = self.get_opt('table')
        validate_host(self.host)
        validate_port(self.port)
        if not self.get_opt('list_tables'):
            validate_chars(self.table, 'hbase table', 'A-Za-z0-9:._-')

    def get_tables(self):
        try:
            return self.conn.tables()
        except socket.timeout as _:
            die('ERROR while trying to get table list: {0}'.format(_))
        except ThriftException as _:
            die('ERROR while trying to get table list: {0}'.format(_))

    def run(self):
        # might have to use compat / transport / protocol args for older versions of HBase or if protocol has been
        # configured to be non-default, see:
        # http://happybase.readthedocs.io/en/stable/api.html#connection
        try:
            log.info('connecting to HBase Thrift Server at %s:%s', self.host, self.port)
            self.conn = happybase.Connection(host=self.host, port=self.port, timeout=10 * 1000)  # ms
        except socket.timeout as _:
            die('ERROR: {0}'.format(_))
        except ThriftException as _:
            die('ERROR: {0}'.format(_))
        tables = self.get_tables()
        if self.get_opt('list_tables'):
            print('Tables:\n\n' + '\n'.join(tables))
            sys.exit(3)
        if self.table not in tables:
            die("HBase table '{0}' does not exist!".format(self.table))
        table = self.conn.table(self.table)
        self.print_table_regions(table)

    def bytes_to_str(self, arg):
        # unfortunately this is passed in a type str, must encode char by char
        #if isStr(arg):
        #    return arg
        #elif isByte(arg):
        #else:
        #    die('unrecognized region name/start/end key, not bytes or string!')
        encode_char = self.encode_char
        return ''.join([ encode_char(x) for x in arg])

    # some extra effort to make it look the same as HBase presents it as
    def encode_char(self, char):
        if char in string.printable and char not in ('\t', '\n', '\r', '\x0b', '\x0c'):
            return char
        else:
            _ = '{0:#0{1}x}'.format(ord(char), 4).replace('0x', '\\x')
            uppercase_callback = lambda x: x.group(1).upper()
            _ = self.re_hex.sub(uppercase_callback, _)
            return _

    def print_table_regions(self, table):
        region_header = 'Region'
        start_key_header = 'Start Key'
        end_key_header = 'End Key'
        server_header = 'Server (host:port)'
        region_width = len(region_header)
        start_key_width = len(start_key_header)
        end_key_width = len(end_key_header)
        server_width = len(server_header)
        separator = '    '
        try:
            for region in table.regions():
                log.debug(region)
                _ = len(self.bytes_to_str(region['name']))
                if _ > region_width:
                    region_width = _
                _ = len(self.bytes_to_str(region['start_key']))
                if _ > start_key_width:
                    start_key_width = _
                _ = len(self.bytes_to_str(region['end_key']))
                if _ > end_key_width:
                    end_key_width = _
                _ = len(region['server_name'] + ':' + str(region['port']))
                if _ > server_width:
                    server_width = _
        except KeyError as _:
            die('error parsing region info: {0}. '.format(_) + support_msg_api())
        total_width = region_width + start_key_width + end_key_width + server_width + len(3 * separator)
        print('=' * total_width)
        print('{region_header:{region_width}}{sep}'
              .format(region_header=region_header, region_width=region_width, sep=separator), end='')
        print('{start_key:{start_key_width}}{sep}'
              .format(start_key=start_key_header, start_key_width=start_key_width, sep=separator), end='')
        print('{end_key:{end_key_width}}{sep}'
              .format(end_key=end_key_header, end_key_width=end_key_width, sep=separator), end='')
        print('{server_header}'.format(server_header=server_header))
        print('=' * total_width)
        try:
            for region in table.regions():
                print('{region:{region_width}}{sep}'
                      .format(region=self.bytes_to_str(region['name']), region_width=region_width, sep=separator), end='')
                print('{start_key:{start_key_width}}{sep}'
                      .format(start_key=self.bytes_to_str(region['start_key']), start_key_width=start_key_width, sep=separator), end='')
                print('{end_key:{end_key_width}}{sep}'
                      .format(end_key=self.bytes_to_str(region['end_key']), end_key_width=end_key_width, sep=separator), end='')
                print('{server}:{port}'.format(server=region['server_name'], port=region['port']))
        except KeyError as _:
            die('error parsing region info: {0}. '.format(_) + support_msg_api())
        # old method
#        log.info('getting hbase:meta table instance')
#        table = self.conn.table('hbase:meta')
#        log.info('scanning hbase:meta')
#        scanner = table.scan(row_prefix=self.table, columns=('info:regioninfo', 'info:server'), sorted_columns=False)
#        start_key_width = 20
#        end_key_width = 20
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
#                                                width=start_key_width + end_key_width + 4), end='\t')
#            print(cf['info:server'])
        log.info('finished, closing connection')
        self.conn.close()


if __name__ == '__main__':
    HBaseShowTableRegionRanges().main()
