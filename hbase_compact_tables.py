#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-04-27 20:49:23 +0100 (Wed, 27 Apr 2016)
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

Tool to iterate on and major compact all HBase tables (to be scheduled and called off-peak)

This is a pythonic rewrite of an old best practice from a few years back when I worked for Cloudera for off-peak
compactions to prevent them impacting peak hours.

Uses the HBase Thrift server. For versions older than HBase 0.96+ or using modified protocols, the connection
protocol / compat / transport settings will need to be adjusted.

Tested on Hortonworks HDP 2.3 (HBase 1.1.2) and Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2, 1.3.1

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import logging
import os
import re
import sys
import traceback
import socket
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
    from harisekhon.utils import log, die
    from harisekhon.utils import validate_host, validate_port, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.4.1'


class HBaseCompactTables(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseCompactTables, self).__init__()
        # Python 3.x
        # super().__init__()
        self.conn = None
        self.host = None
        self.port = 9090
        self.table_regex = None
        self.timeout_default = 6 * 3600

    def add_options(self):
        self.add_hostoption(name='HBase Thrift Server', default_host='localhost', default_port=self.port)
        self.add_opt('-r', '--regex', help='Regex of tables to compact' +
                     '. Highly recommended to use this to compact a different subset of tables each night' +
                     ' to prevent the last running compaction running in to business hours')
        self.add_opt('-l', '--list-tables', action='store_true', help='List tables and exit')

    def process_args(self):
        log.setLevel(logging.INFO)
        self.no_args()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        validate_host(self.host)
        validate_port(self.port)
        # happybase socket requires an integer type
        self.port = int(self.port)
        regex = self.get_opt('regex')
        if regex:
            validate_regex(regex)
            self.table_regex = re.compile(regex, re.I)
            log.info("filtering to compact only tables matching regex \'%s\'", regex)

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
        except (socket.timeout, ThriftException, HBaseIOError) as _:
            die('ERROR: {0}'.format(_))
        tables = self.get_tables()
        if self.get_opt('list_tables'):
            print('Tables:\n\n' + '\n'.join(tables))
            sys.exit(3)
        for table in tables:
            if self.table_regex:
                if self.table_regex.search(table):
                    self.compact_table(table)
            else:
                self.compact_table(table)
        log.info('finished, closing connection')
        self.conn.close()

    def compact_table(self, table):
        log.info("major compacting table '%s'", table)
        try:
            self.conn.compact_table(table, major=True)
        except (socket.timeout, ThriftException, HBaseIOError) as _:
            die('ERROR while trying to compact table \'{0}\': {1}'.format(table, _))


if __name__ == '__main__':
    HBaseCompactTables().main()
