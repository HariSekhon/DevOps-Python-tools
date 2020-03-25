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

Connect to HiveServer2 and count number of rows with only NULLs in all columns
for each table in each database, or only those matching given db / table regexes

Useful for catching problems with data quality or subtle ETL bugs

Rewrite of a Perl version from 2013 from my DevOps Perl Tools repo

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
__version__ = '0.6.0'


class HiveTablesNullRows(HiveForEachTable):

    def __init__(self):
        # Python 2.x
        super(HiveTablesNullRows, self).__init__()
        # Python 3.x
        # super().__init__()
        self.query = 'placeholder'  # constructed later dynamically per table, here to suppress --query CLI option
        self.database = None
        self.table = None
        #self.partition = None
        self.ignore_errors = False

    # discard last param query and construct our own based on the table DDL of cols
    def execute(self, conn, database, table, _):
        columns = []
        log.info("describing table '%s.%s'", database, table)
        with conn.cursor() as column_cursor:
            # impala library doesn't support parameterized query quoting from dbapi spec
            #column_cursor.execute('use %(database)s', {'database': database})
            #column_cursor.execute('describe %(table)s', {'table': table})
            column_cursor.execute('use `{}`'.format(database))
            column_cursor.execute('describe `{}`'.format(table))
            for column_row in column_cursor:
                column = column_row[0]
                #column_type = column_row[1]
                columns.append(column)
        query = self.generate_sql(database, table, columns)
        with conn.cursor() as table_cursor:
            log.debug('executing query:  %s', query)
            table_cursor.execute(query)
            for result in table_cursor:
                count = result[0]
                print('{db}.{table}\t{count}'.format(db=database, table=table, count=count))

    @staticmethod
    def generate_sql(database, table, columns):
        sql = "SELECT count(*) FROM `{db}`.`{table}` WHERE `"\
              .format(db=database, table=table) + \
              "` IS NULL AND `".join(columns) + "` IS NULL"
        return sql


if __name__ == '__main__':
    HiveTablesNullRows().main()
