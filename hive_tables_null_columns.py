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

Connect to HiveServer2 and find tables with columns containing only NULLs
for all tables in all databases, or only those matching given db / table regexes

Describes each table, constructs a complex query to check each column individually for containing only NULLs,
and prints out each tables' count of total columns containing only NULLs as well as the list of offending columns

Useful for catching problems with data quality or subtle ETL bugs

Rewrite of a Perl version from 2014 from my DevOps Perl Tools repo

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
import sys
srcdir = os.path.abspath(os.path.dirname(__file__))
pylib = os.path.join(srcdir, 'pylib')
sys.path.append(pylib)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log
    from hive_foreach_table import HiveForEachTable
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)


__author__ = 'Hari Sekhon'
__version__ = '0.5.0'


class HiveTablesNullColumns(HiveForEachTable):

    def __init__(self):
        # Python 2.x
        super(HiveTablesNullColumns, self).__init__()
        # Python 3.x
        # super().__init__()
        self.query = 'placeholder'  # constructed later dynamically per table, here to suppress --query CLI option
        self.database = None
        self.table = None
        #self.partition = None
        self.ignore_errors = False

    # discard last param query and construct our own based on the table DDL of cols
    def execute(self, conn, database, table, _query):
        sum_part = ''
        columns = []
        log.info("describing table '%s.%s'", database, table)
        with conn.cursor() as column_cursor:
            # doesn't support parameterized query quoting from dbapi spec
            #column_cursor.execute('use %(database)s', {'database': database})
            #column_cursor.execute('describe %(table)s', {'table': table})
            column_cursor.execute('use `{}`'.format(database))
            column_cursor.execute('describe `{}`'.format(table))
            for column_row in column_cursor:
                column = column_row[0]
                #column_type = column_row[1]
                columns.append(column)
        sum_part = ', '.join(
            ['IF(SUM(IF(`{col}` IS NULL, 1, 0)) = COUNT(*), 1, 0) as `{col}`'.format(col=column) \
            for column in columns]
        )
        query = "SELECT {sum_part} FROM `{db}`.`{table}` WHERE `"\
                .format(sum_part=sum_part, db=database, table=table) + \
                "` IS NULL OR `".join(columns) + "` IS NULL"
        self.check_table_for_nulls(conn, database, table, columns, query)

    @staticmethod
    def check_table_for_nulls(conn, database, table, columns, query):
        with conn.cursor() as table_cursor:
            log.debug('executing query:  %s', query)
            table_cursor.execute(query)
            cols_with_nulls = []
            for result in table_cursor:
                # tuple of ints (0, 0, 0, .... N) - one per column
                for index in range(len(list(result))):
                    col_result = result[index]
                    if col_result > 0:
                        cols_with_nulls.append(columns[index])
                num_cols = len(cols_with_nulls)
                total_cols = len(columns)
                if cols_with_nulls:
                    print('WARNING: {db}.{table} has {num}/{total} columns with only NULLs: {cols}'\
                          .format(db=database,
                                  table=table,
                                  num=num_cols,
                                  total=total_cols,
                                  cols=', '.join(sorted(cols_with_nulls))
                                 )
                         )
                else:
                    print('OK: {db}.{table} has {num}/{total} columns with only nulls'\
                          .format(db=database, table=table, num=num_cols, total=total_cols))


if __name__ == '__main__':
    HiveTablesNullColumns().main()
