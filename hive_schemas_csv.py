#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-11-07 14:52:38 +0000 (Thu, 07 Nov 2019)
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

Connect to HiveServer2 and dump all the schemas, tables and columns out in CSV format to stdout

In practice Hive is much more reliable than Impala for dumping masses of schema

Impala appears faster initially but then slows down more than Hive and hits things query handle errors
under sustained load of extracting large amounts of schema information

There is also a risk that Impala's metadata may be out of date, so Hive is strongly preferred for this


CSV format:

database,table,column,type


I recommend generating quoted csv because you may encounter Hive data types such as decimal(15,2)
which would cause incorrect field splitting, you can disable by setting --quotechar='' to blank but
if escaping is needed then you will be forced to specify an --escapechar otherwise the csv writer will
raise a traceback to tell you to set one (eg. --escapechar='\\')

Tested on Hive 1.1.0 on CDH 5.10, 5.16 with Kerberos and SSL

Due to a thrift / impyla bug this needs exactly thrift==0.9.3, see

https://github.com/cloudera/impyla/issues/286

If you get an error like this:

ERROR:impala.hiveserver2:Failed to open transport (tries_left=1)
...
TTransportException: TSocket read 0 bytes

then check your --kerberos and --ssl settings match the cluster's settings
(Thrift and Kerberos have the worst error messages ever)

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import csv
import os
import sys
import impala
srcdir = os.path.abspath(os.path.dirname(__file__))
pylib = os.path.join(srcdir, 'pylib')
lib = os.path.join(srcdir, 'lib')
sys.path.append(pylib)
sys.path.append(lib)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log
    from hive_impala_cli import HiveImpalaCLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.5.1'


class HiveSchemasCSV(HiveImpalaCLI):

    def __init__(self):
        # Python 2.x
        super(HiveSchemasCSV, self).__init__()
        # Python 3.x
        # super().__init__()
        self.delimiter = None
        self.quotechar = None
        self.escapechar = None
        self.table_count = 0
        self.column_count = 0
        self.ignore_errors = False
        self.csv_writer = None
        self.conn = None

    def add_options(self):
        super(HiveSchemasCSV, self).add_options()
        # must set type to str otherwise csv module gives this error on Python 2.7:
        # TypeError: "delimiter" must be string, not unicode
        # type=str worked with argparse but when integrated with CLI then 'from __future__ import unicode_literals'
        # breaks this - might break in Python 3 if the impyla module doesn't fix behaviour
        self.add_opt('-d', '--delimiter', default=',', type=str, help='Delimiter to use (default: ,)')
        self.add_opt('-Q', '--quotechar', default='"', type=str,
                     help='Generate quoted CSV (recommended, default is double quote \'"\')')
        self.add_opt('-E', '--escapechar', help='Escape char if needed')
#
# ignore tables that fail with errors like:
#
# Hive (CDH has MR, no tez):
#
# impala.error.OperationalError: Error while processing statement: FAILED: Execution Error, return code 1 from org.apache.hadoop.hive.ql.exec.mr.MapRedTask  # pylint: disable=line-too-long
#
# Impala:
#
# impala.error.HiveServer2Error: AnalysisException: Unsupported type 'void' in column '<column>' of table '<table>'
# CAUSED BY: TableLoadingException: Unsupported type 'void' in column '<column>' of table '<table>'
#
        self.add_opt('-e', '--ignore-errors', action='store_true',
                     help='Ignore individual table schema listing errors (Impala often has table metadata errors)')

    def process_options(self):
        super(HiveSchemasCSV, self).process_options()
        self.delimiter = self.get_opt('delimiter')
        self.quotechar = self.get_opt('quotechar')
        self.escapechar = self.get_opt('escapechar')
        self.ignore_errors = self.get_opt('ignore_errors')

    def run(self):

        self.conn = self.connect('default')

        quoting = csv.QUOTE_ALL
        if self.quotechar == '':
            quoting = csv.QUOTE_NONE
        fieldnames = ['database', 'table', 'column', 'type']
        self.csv_writer = csv.DictWriter(sys.stdout,
                                         delimiter=self.delimiter,
                                         quotechar=self.quotechar,
                                         escapechar=self.escapechar,
                                         quoting=quoting,
                                         fieldnames=fieldnames)
        self.csv_writer.writeheader()
        log.info('querying databases')
        databases = []
        database_count = 0
        with self.conn.cursor() as db_cursor:
            db_cursor.execute('show databases')
            for db_row in db_cursor:
                database = db_row[0]
                database_count += 1
                databases.append(database)
        log.info('found %s databases', database_count)
        for database in databases:
            self.process_database(database)
        log.info('databases: %s, tables: %s, columns: %s', database_count, self.table_count, self.column_count)

    def process_database(self, database):
        log.info("querying tables for database '%s'", database)
        tables = []
        with self.conn.cursor() as table_cursor:
            # doesn't support parameterized query quoting from dbapi spec
            #table_cursor.execute('use %(database)s', {'database': database})
            table_cursor.execute('use `{}`'.format(database))
            table_cursor.execute('show tables')
            for table_row in table_cursor:
                table = table_row[0]
                self.table_count += 1
                tables.append(table)
        log.info("found %s tables in database '%s'", len(tables), database)
        for table in tables:
            try:
                self.process_table(database, table)
            except impala.error.HiveServer2Error as _:
                if self.ignore_errors:
                    log.error("database '%s' table '%s':  %s", database, table, _)
                    continue
                raise

    def process_table(self, database, table):
        log.info("describing table '%s.%s'", database, table)
        with self.conn.cursor() as column_cursor:
            # doesn't support parameterized query quoting from dbapi spec
            #column_cursor.execute('use %(database)s', {'database': database})
            #column_cursor.execute('describe %(table)s', {'table': table})
            column_cursor.execute('use `{}`'.format(database))
            column_cursor.execute('describe `{}`'.format(table))
            column_count = 0
            for column_row in column_cursor:
                column = column_row[0]
                column_type = column_row[1]
                column_count += 1
                self.csv_writer.writerow({'database': database,
                                          'table': table,
                                          'column': column,
                                          'type': column_type})
        log.info("found %s columns in table '%s.%s'", column_count, database, table)
        self.column_count += column_count


if __name__ == '__main__':
    HiveSchemasCSV().main()
