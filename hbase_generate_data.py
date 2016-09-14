#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-09-14 15:19:35 +0200 (Wed, 14 Sep 2016)
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

Tool to generate some random data in HBase for test purposes

Uses the HBase Thrift server. For versions older than HBase 0.96+ or using modified protocols, the connection
protocol / compat / transport settings will need to be adjusted.

Prints a dot for every 100 rows sent to let you know it's still working.

Tested on Hortonworks HDP 2.3 (HBase 1.1.2) and Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import logging
import os
import sys
import time
import traceback
import socket
import happybase
import thrift
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, die, random_alnum, autoflush
    from harisekhon.utils import validate_host, validate_port, validate_database_tablename, validate_int
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'


class HBaseGenerateData(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseGenerateData, self).__init__()
        # Python 3.x
        # super().__init__()
        self.conn = None
        self.host = None
        self.port = 9090
        self.default_table_name = 'HS_test_data'
        self.default_num_rows = 10000
        self.default_key_len = 20
        self.default_value_len = 40
        self.table = self.default_table_name
        self.num_rows = self.default_num_rows
        self.key_len = self.default_key_len
        self.value_len = self.default_value_len
        self.skew = False
        self.drop_table = False
        self.timeout_default = 6 * 3600
        autoflush()

    def add_options(self):
        self.add_hostoption(name='HBase Thrift Server', default_host='localhost', default_port=self.port)
        self.add_opt('-T', '--table', default=self.default_table_name, help='Table to create with the generated data.' +
                     ' Will refuse to send data to any already existing table for safety reasons')
        self.add_opt('-n', '--num', default=self.default_num_rows,
                     help='Number of rows to generate (default {0})'.format(self.default_num_rows))
        self.add_opt('-K', '--key-len', default=self.default_key_len,
                     help='Key length (default: {0})'.format(self.default_key_len))
        self.add_opt('-L', '--value-len', default=self.default_value_len,
                     help='Value length (default: {0})'.format(self.default_value_len))
        self.add_opt('-S', '--skew', action='store_true', default=False,
                     help='Skew the data row keys intentionally for testing (default: False, NOT IMPLEMENTED YET)')
        self.add_opt('-d', '--drop-table', action='store_true', default=False,
                     help='Drop test data table (only allowed if keeping the default table name for safety)')

    def process_args(self):
        log.setLevel(logging.INFO)
        self.no_args()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        validate_host(self.host)
        validate_port(self.port)
        self.table = self.get_opt('table')
        self.num_rows = self.get_opt('num')
        self.key_len = self.get_opt('key_len')
        self.value_len = self.get_opt('value_len')
        self.skew = self.get_opt('skew')
        self.drop_table = self.get_opt('drop_table')
        validate_database_tablename(self.table)
        validate_int(self.num_rows, 'num rows', 1, 1000000000)
        validate_int(self.key_len, 'key length', 10, 1000)
        validate_int(self.value_len, 'value length', 1, 1000000)
        self.num_rows = int(self.num_rows)
        if self.drop_table and self.table != self.default_table_name:
            die("not allowed to use --drop-table if using a table name other than the default table '{0}'"\
                .format(self.default_table_name))

    def get_tables(self):
        try:
            return self.conn.tables()
        except socket.timeout as _:
            die('ERROR while trying to get table list: {0}'.format(_))
        except thrift.transport.TTransport.TTransportException as _:
            die('ERROR while trying to get table list: {0}'.format(_))

    def run(self):
        # might have to use compat / transport / protocol args for older versions of HBase or if protocol has been
        # configured to be non-default, see:
        # http://happybase.readthedocs.io/en/stable/api.html#connection
        try:
            log.info('connecting to HBase Thrift Server at {0}:{1}'.format(self.host, self.port))
            self.conn = happybase.Connection(host=self.host, port=self.port, timeout=10 * 1000)  # ms
        except socket.timeout as _:
            die('ERROR: {0}'.format(_))
        except thrift.transport.TTransport.TTransportException as _:
            die('ERROR: {0}'.format(_))
        tables = self.get_tables()
        # of course there is a minor race condition here between getting the table list, checking and creating
        # not sure if it's solvable, if you have any idea of how to solve it please let me know, even locking
        # would only protect again multiple runs of this script on the same machine...
        if self.table in tables:
            if self.drop_table:
                log.info("table '%s' already existed but -d / --drop-table was specified, removing table first",
                         self.table)
                self.conn.delete_table(self.table, disable=True)
            else:
                die("WARNING: table '{0}' already exists, will not send data to a pre-existing table for safety"\
                    .format(self.table))
        self.create_table()
        self.populate_table()
        log.info('finished, closing connection')
        self.conn.close()

    def create_table(self):
        log.info('creating table %s', self.table)
        self.conn.create_table(self.table, {'cf1': dict(max_versions=1)})

    def populate_table(self):
        table = self.table
        key_len = self.key_len
        value_len = self.value_len
        table_conn = None
        # does not actually connect until sending data
        #log.info("connecting to test table '%s'", table)
        try:
            table_conn = self.conn.table(table)
        except socket.timeout as _:
            die('ERROR while trying to connect to table \'{0}\': {1}'.format(table, _))
        except thrift.transport.TTransport.TTransportException as _:
            die('ERROR while trying to connect to table \'{0}\': {1}'.format(table, _))
        log.info("populating test table '%s' with random data", table)
        try:
            start = time.time()
            for _ in range(self.num_rows):
                table_conn.put(bytes(random_alnum(key_len)), {b'cf1:col1': bytes(random_alnum(value_len))})
                if _ % 100 == 0:
                    print('.', end='')
            print()
            time_taken = time.time() - start
            log.info('sent %s rows of generated data to HBase in %.2f seconds', self.num_rows, time_taken)
        except socket.timeout as _:
            die('ERROR while trying to populate table \'{0}\': {1}'.format(table, _))
        except thrift.transport.TTransport.TTransportException as _:
            die('ERROR while trying to populate table \'{0}\': {1}'.format(table, _))


if __name__ == '__main__':
    HBaseGenerateData().main()
