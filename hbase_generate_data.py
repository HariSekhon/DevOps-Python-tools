#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-09-14 15:19:35 +0200 (Wed, 14 Sep 2016)
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

Tool to generate some random data in HBase for test purposes

Uses the HBase Thrift server. For versions older than HBase 0.96+ or using modified protocols, the connection
protocol / compat / transport settings will need to be adjusted.

Prints a dot for every 100 rows sent to let you know it's still working.

Tested on Hortonworks HDP 2.3 (HBase 1.1.2) and Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2, 1.3.1

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

#import logging
import os
import sys
import time
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
    import humanize
except ImportError as _:
    print('module import error - did you forget to build this project?\n\n'
          + traceback.format_exc(), end='')
    sys.exit(4)
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, die, random_alnum, autoflush, log_option
    from harisekhon.utils import validate_host, validate_port, validate_database_tablename, validate_int
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.5.2'


class HBaseGenerateData(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseGenerateData, self).__init__()
        # Python 3.x
        # super().__init__()
        self.conn = None
        self.host = None
        self.port = 9090
        self.verbose_default = 2
        self.default_table_name = 'HS_test_data'
        self.default_num_rows = 10000
        self.default_key_length = 20
        self.default_value_length = 40
        self.default_skew_pc = 90
        self.table = self.default_table_name
        self.num_rows = self.default_num_rows
        self.key_length = self.default_key_length
        self.value_length = self.default_value_length
        self.skew = False
        self.skew_pc = self.default_skew_pc
        self.drop_table = False
        self.use_existing_table = False
        self.column_family = 'cf1'
        self.timeout_default = 6 * 3600
        autoflush()

    def add_options(self):
        self.add_hostoption(name='HBase Thrift Server', default_host='localhost', default_port=self.port)
        self.add_opt('-T', '--table', default=self.default_table_name, help='Table to create with the generated data.' +
                     ' Will refuse to send data to any already existing table for safety reasons')
        self.add_opt('-n', '--num', default=self.default_num_rows,
                     help='Number of rows to generate (default {0})'.format(self.default_num_rows))
        self.add_opt('-K', '--key-length', default=self.default_key_length,
                     help='Key length (default: {0})'.format(self.default_key_length))
        self.add_opt('-L', '--value-length', default=self.default_value_length,
                     help='Value length (default: {0})'.format(self.default_value_length))
        self.add_opt('-s', '--skew', action='store_true', default=False,
                     help='Skew the data row keys intentionally for testing (default: False). This will use a key of ' +
                     'all \'A\'s of length --key-length, plus a numerically incrementing padded suffix')
        self.add_opt('--skew-percentage', '--pc', default=self.default_skew_pc,
                     help='Skew percentage (default: {0})'.format(self.default_skew_pc))
        self.add_opt('-d', '--drop-table', action='store_true', default=False,
                     help='Drop test data table (only allowed if keeping the default table name for safety)')
        self.add_opt('-X', '--use-existing-table', action='store_true',
                     help='Allows sending data to an existing table. ' +
                     'Dangerous but useful to test pre-splitting schemes on test tables')

    def process_args(self):
        # this resets DEBUG env var
        #log.setLevel(logging.INFO)
        self.no_args()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        validate_host(self.host)
        validate_port(self.port)
        # happybase socket requires an integer
        self.port = int(self.port)

        self.table = self.get_opt('table')
        self.num_rows = self.get_opt('num')
        self.key_length = self.get_opt('key_length')
        self.value_length = self.get_opt('value_length')

        validate_database_tablename(self.table)
        validate_int(self.num_rows, 'num rows', 1, 1000000000)
        validate_int(self.key_length, 'key length', 10, 1000)
        validate_int(self.value_length, 'value length', 1, 1000000)

        self.num_rows = int(self.num_rows)

        self.skew = self.get_opt('skew')
        log_option('skew data', self.skew)
        self.skew_pc = self.get_opt('skew_percentage')
        validate_int(self.skew_pc, 'skew percentage', 0, 100)
        self.skew_pc = int(self.skew_pc)
        self.drop_table = self.get_opt('drop_table')
        self.use_existing_table = self.get_opt('use_existing_table')

        if self.drop_table and self.table != self.default_table_name:
            die("not allowed to use --drop-table if using a table name other than the default table '{0}'"\
                .format(self.default_table_name))

    def get_tables(self):
        try:
            log.info('getting table list')
            return self.conn.tables()
        except (socket.timeout, ThriftException, HBaseIOError) as _:
            die('ERROR while trying to get table list: {0}'.format(_))

    def run(self):
        # might have to use compat / transport / protocol args for older versions of HBase or if protocol has been
        # configured to be non-default, see:
        # http://happybase.readthedocs.io/en/stable/api.html#connection
        try:
            log.info('connecting to HBase Thrift Server at {0}:{1}'.format(self.host, self.port))
            self.conn = happybase.Connection(host=self.host, port=self.port, timeout=10 * 1000)  # ms
            tables = self.get_tables()
            # of course there is a minor race condition here between getting the table list, checking and creating
            # not sure if it's solvable, if you have any idea of how to solve it please let me know, even locking
            # would only protect again multiple runs of this script on the same machine...
            if self.table in tables:
                if self.drop_table:
                    log.info("table '%s' already existed but -d / --drop-table was specified, removing table first",
                             self.table)
                    self.conn.delete_table(self.table, disable=True)
                    # wait up to 30 secs for table to be deleted
                    #for _ in range(30):
                    #    if self.table not in self.get_tables():
                    #        break
                    #    log.debug('waiting for table to be deleted before creating new one')
                    #    time.sleep(1)
                elif self.use_existing_table:
                    pass
                else:
                    die("WARNING: table '{0}' already exists, will not send data to a pre-existing table for safety"\
                        .format(self.table) +
                        ". You can choose to either --drop-table or --use-existing-table")
            if not self.use_existing_table:
                self.create_table()
            self.populate_table()
            log.info('finished, closing connection')
            self.conn.close()
        except (socket.timeout, ThriftException, HBaseIOError) as _:
            die('ERROR: {0}'.format(_))

    def create_table(self):
        log.info('creating table %s', self.table)
        self.conn.create_table(self.table, {self.column_family: dict(max_versions=1)})

    def populate_table(self):
        table = self.table
        key_length = self.key_length
        value_length = self.value_length
        table_conn = None
        # does not actually connect until sending data
        #log.info("connecting to test table '%s'", table)
        try:
            table_conn = self.conn.table(table)
        except (socket.timeout, ThriftException, HBaseIOError) as _:
            die('ERROR while trying to connect to table \'{0}\': {1}'.format(table, _))
        log.info("populating test table '%s' with random data", table)
        if self.use_existing_table:
            self.column_family = sorted(table_conn.families().keys())[0]
        cf_col = self.column_family + ':col1'
        try:
            skew_prefix = 'A' * key_length
            skew_mod = max(1, 100.0 / self.skew_pc)
            #log.info('skew mod is %s', skew_mod)
            width = len('{0}'.format(self.num_rows))
            start = time.time()
            for _ in range(self.num_rows):
                if self.skew and int(_ % skew_mod) == 0:
                    table_conn.put(bytes(skew_prefix + '{number:0{width}d}'.format(width=width, number=_)), \
                                   {bytes(cf_col): bytes(random_alnum(value_length))})
                else:
                    table_conn.put(bytes(random_alnum(key_length)), {bytes(cf_col): bytes(random_alnum(value_length))})
                if _ % 100 == 0:
                    print('.', file=sys.stderr, end='')
            print(file=sys.stderr)
            time_taken = time.time() - start
            log.info('sent %s rows of generated data to HBase in %.2f seconds (%d rows/sec, %s/sec)',
                     self.num_rows,
                     time_taken,
                     self.num_rows / time_taken,
                     humanize.naturalsize(self.num_rows * (key_length + value_length) / time_taken)
                    )
        except (socket.timeout, ThriftException, HBaseIOError) as _:
            exp = str(_)
            exp = exp.replace('\\n', '\n')
            exp = exp.replace('\\t', '\t')
            die('ERROR while trying to populate table \'{0}\': {1}'.format(table, exp))


if __name__ == '__main__':
    HBaseGenerateData().main()
