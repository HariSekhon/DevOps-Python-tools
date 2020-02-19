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

Connect to HiveServer2 and execute a query for each table in each database,
or only those matching given db / table regexes

Useful for getting row counts of all tables or analyzing tables:

eg.

hive_foreach_table.py --query 'SELECT COUNT(*) FROM {db}.{table}'
hive_foreach_table.py --query 'ANALYZE TABLE {db}.{table} COMPUTE STATS'

or just for today's partition:

hive_foreach_table.py --query "ANALYZE TABLE {db}.{table} PARTITION(date=$(date '+%Y-%m-%d')) COMPUTE STATS"


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
__version__ = '0.5.2'


class HiveForEachTable(HiveImpalaCLI):

    def __init__(self):
        # Python 2.x
        super(HiveForEachTable, self).__init__()
        # Python 3.x
        # super().__init__()

        # self.query can be pre-defined in which case subclassed programs won't expose --query option
        self.query = None
        self.database = None
        self.table = None
        self.partition = None
        self.ignore_errors = False
        self.table_count = 0

    def add_options(self):
        super(HiveForEachTable, self).add_options()
        # allow subclassing to pre-define query and not expose option in that case
        if self.query is None:
            self.add_opt('-q', '--query', help='Query or statement to execute for each table' + \
                         ' (replaces {db} and {table} in the query string with each table and its database)')
        self.add_opt('-d', '--database', default='.*', help='Database regex (default: .*)')
        self.add_opt('-t', '--table', default='.*', help='Table regex (default: .*)')
        #self.add_opt('-p', '--partition', default='.*', help='Partition regex (default: .*)')
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
        super(HiveForEachTable, self).process_options()
        if self.query is None:
            self.query = self.get_opt('query')
        if not self.query:
            self.usage('query not defined')
        self.database = self.get_opt('database')
        self.table = self.get_opt('table')
        #self.partition = self.get_opt('partition')
        self.ignore_errors = self.get_opt('ignore_errors')
        validate_regex(self.database, 'database')
        validate_regex(self.table, 'table')
        #validate_regex(self.partition, 'partition')

    def run(self):
        database_regex = re.compile(self.database, re.I)
        table_regex = re.compile(self.table, re.I)
        #partition_regex = re.compile(self.partition, re.I)
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
            self.process_database(database, table_regex)
        log.info('processed %s databases, %s tables', database_count, self.table_count)

    def process_database(self, database, table_regex):
        tables = []
        table_count = 0
        log.info("querying tables for database '%s'", database)
        conn = self.connect(database)
        with conn.cursor() as table_cursor:
            try:
                # doesn't support parameterized query quoting from dbapi spec
                #table_cursor.execute('use %(database)s', {'database': database})
                table_cursor.execute('use `{}`'.format(database))
                table_cursor.execute('show tables')
            except impala.error.HiveServer2Error as _:
                log.error("error querying tables for database '%s': %s", database, _)
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
                query = self.query.format(db='`{}`'.format(database),
                                          table='`{}`'.format(table))
            except KeyError as _:
                if _ == 'db':
                    query = self.query.format(table='`{}`'.format(table))
                else:
                    raise
            try:
                self.execute(conn, database, table, query)
                self.table_count += 1
            except Exception as _:
                if self.ignore_errors:
                    log.error("database '%s' table '%s':  %s", database, table, _)
                    continue
                raise

    @staticmethod
    def execute(conn, database, table, query):
        try:
            log.info(' %s.%s - running %s', database, table, query)
            with conn.cursor() as query_cursor:
                # doesn't support parameterized query quoting from dbapi spec
                query_cursor.execute(query)
                for result in query_cursor:
                    print('{db}.{table}\t{result}'.format(db=database, table=table, \
                                                          result='\t'.join([str(_) for _ in result])))
        #except (impala.error.OperationalError, impala.error.HiveServer2Error) as _:
        #    log.error(_)
        except impala.error.ProgrammingError as _:
            log.error(_)
            # COMPUTE STATS returns no results
            if 'Trying to fetch results on an operation with no results' not in str(_):
                raise


if __name__ == '__main__':
    HiveForEachTable().main()
