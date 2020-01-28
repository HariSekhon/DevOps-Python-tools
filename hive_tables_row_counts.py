#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-11-26 10:08:52 +0000 (Tue, 26 Nov 2019)
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

Connect to HiveServer2 and get rows counts for all tables in all databases,
or only those matching given db / table / partition value regexes

Useful for reconciliations between clusters after migrations

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
from __future__ import unicode_literals

import os
import re
import sys
import impala
srcdir = os.path.abspath(os.path.dirname(__file__))
pylib = os.path.join(srcdir, 'pylib')
lib = os.path.join(srcdir, 'lib')
sys.path.append(pylib)
sys.path.append(lib)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, validate_regex
    from hive_impala_cli import HiveImpalaCLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.1'


class HiveTablesRowCounts(HiveImpalaCLI):

    def __init__(self):
        # Python 2.x
        super(HiveTablesRowCounts, self).__init__()
        # Python 3.x
        # super().__init__()
        self.database = None
        self.table = None
        self.partition = None
        self.ignore_errors = False
        self.table_count = 0

    def add_options(self):
        super(HiveTablesRowCounts, self).add_options()
        self.add_opt('-d', '--database', default='.*', help='Database regex (default: .*)')
        self.add_opt('-t', '--table', default='.*', help='Table regex (default: .*)')
        self.add_opt('-p', '--partition', default='.*', help='Partition regex (default: .*)')
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
        self.add_opt('-e', '--ignore-errors', action='store_true', help='Ignore individual table errors and continue')

    def process_options(self):
        super(HiveTablesRowCounts, self).process_options()
        self.database = self.get_opt('database')
        self.table = self.get_opt('table')
        self.partition = self.get_opt('partition')
        self.ignore_errors = self.get_opt('ignore_errors')
        validate_regex(self.database, 'database')
        validate_regex(self.table, 'table')
        validate_regex(self.partition, 'partition')

    def run(self):
        database_regex = re.compile(self.database, re.I)
        table_regex = re.compile(self.table, re.I)
        partition_regex = re.compile(self.partition, re.I)
        conn = self.connect('default')
        log.info('querying databases')
        # collecting in local list because long time iteration results in
        # impala.error.HiveServer2Error: Invalid query handle
        databases = []
        database_count = 0
        with conn.cursor() as db_cursor:
            db_cursor.execute('show databases')
            for db_row in db_cursor:
                database = db_row[0]
                database_count += 1
                if not database_regex.search(database):
                    log.debug("skipping database '%s', does not match regex '%s'", database, self.database)
                    continue
                databases.append(database)
        log.info('%s/%s databases selected', len(databases), database_count)
        for database in databases:
            self.process_database(conn, database, table_regex, partition_regex)
        log.info('processed %s databases, %s tables', database_count, self.table_count)

    def process_database(self, conn, database, table_regex, partition_regex):
        tables = []
        table_count = 0
        log.info("querying tables for database '%s'", database)
        with conn.cursor() as table_cursor:
            try:
                # doesn't support parameterized query quoting from dbapi spec
                #table_cursor.execute('use %(database)s', {'database': database})
                table_cursor.execute('use `{}`'.format(database))
                table_cursor.execute('show tables')
            except impala.error.HiveServer2Error as _:
                log.error(_)
                if 'AuthorizationException' in str(_):
                    return
                raise
            for table_row in table_cursor:
                table = table_row[0]
                table_count += 1
                if not table_regex.search(table):
                    log.debug("skipping database '%s' table '%s', does not match regex '%s'", \
                              database, table, self.table)
                    continue
                tables.append(table)
        log.info("%s/%s tables selected for database '%s'", len(tables), table_count, database)
        for table in tables:
            try:
                self.get_row_counts(conn, database, table, partition_regex)
                self.table_count += 1
            except Exception as _:
                # invalid query handle and similar errors happen at higher level
                # as they are not query specific, will not be caught here so still error out
                if self.ignore_errors:
                    log.error("database '%s' table '%s':  %s", database, table, _)
                    continue
                raise

    def get_row_counts(self, conn, database, table, partition_regex):
        log.info("getting partitions for database '%s' table '%s'", database, table)
        with conn.cursor() as partition_cursor:
            # doesn't support parameterized query quoting from dbapi spec
            partition_cursor.execute('use `{db}`'.format(db=database))
            try:
                partition_cursor.execute('show partitions `{table}`'.format(table=table))
                for partitions_row in partition_cursor:
                    partition_key = partitions_row[0]
                    partition_value = partitions_row[1]
                    if not partition_regex.match(partition_value):
                        log.debug("skipping database '%s' table '%s' partition key '%s' value '%s', " +
                                  "value does not match regex '%s'",
                                  database,
                                  table,
                                  partition_key,
                                  partition_value,
                                  self.partition)
                        continue
                    # doesn't support parameterized query quoting from dbapi spec
                    partition_cursor.execute('SELECT COUNT(*) FROM `{db}`.`{table}` WHERE `{key}`={value}'\
                                          .format(db=database, table=table, key=partition_key, value=partition_value))
                    for result in partition_cursor:
                        row_count = result[0]
                        print('{db}.{table}.{key}={value}\t{row_count}'.format(\
                                db=database,
                                table=table,
                                key=partition_key,
                                value=partition_value,
                                row_count=row_count))
            except (impala.error.OperationalError, impala.error.HiveServer2Error) as _:
                # Hive impala.error.HiveServer2Error: is not a partitioned table
                # Impala impala.error.HiveServer2Error: Table is not partitioned
                if 'is not a partitioned table' not in str(_) and \
                   'Table is not partitioned' not in str(_):
                    raise
                log.info("no partitions found for database '%s' table '%s', getting row counts for whole table",
                         database, table)
                with conn.cursor() as table_cursor:
                    log.info("running SELECT COUNT(*) FROM `%s`.`%s`", database, table)
                    # doesn't support parameterized query quoting from dbapi spec
                    table_cursor.execute('SELECT COUNT(*) FROM `{db}`.`{table}`'.format(db=database, table=table))
                    for result in table_cursor:
                        row_count = result[0]
                        print('{db}.{table}\t{row_count}'.format(db=database, table=table, row_count=row_count))


if __name__ == '__main__':
    HiveTablesRowCounts().main()
