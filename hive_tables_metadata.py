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

Connect to HiveServer2 and print the first matching DDL metadata field (eg. 'Location')
for each table in each database, or only those matching given db / table regexes

Examples (fields are case sensitive regex and return N/A without match):

./hive_tables_metadata.py --field Location ...
./hive_tables_metadata.py --field SerDe ...

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
srcdir = os.path.abspath(os.path.dirname(__file__))
pylib = os.path.join(srcdir, 'pylib')
sys.path.append(pylib)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, validate_regex
    from hive_foreach_table import HiveForEachTable
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.5.1'


class HiveTablesMetadata(HiveForEachTable):

    def __init__(self):
        # Python 2.x
        super(HiveTablesMetadata, self).__init__()
        # Python 3.x
        # super().__init__()
        self.query = 'describe formatted {table}'
        self.field = None

    def add_options(self):
        # Python 2.x
        super(HiveTablesMetadata, self).add_options()
        # Python 3.x
        # super().__init__()
        if self.field is None:
            self.add_opt('-f', '--field', help='Table DDL metadata field to return for each table (required)')

    def process_options(self):
        # Python 2.x
        super(HiveTablesMetadata, self).process_options()
        # Python 3.x
        # super().__init__()
        if self.field is None:
            self.field = self.get_opt('field')
        if not self.field:
            self.usage('--field not specified')
        validate_regex(self.field, 'field')
        self.field = re.compile(self.field)

    # discard last param query and construct our own based on the table DDL of cols
    def execute(self, conn, database, table, query):
        log.info("describing table '%s.%s'", database, table)
        field = 'N/A'
        with conn.cursor() as table_cursor:
            # doesn't support parameterized query quoting from dbapi spec
            #table_cursor.execute('use %(database)s', {'database': database})
            #table_cursor.execute('describe %(table)s', {'table': table})
            table_cursor.execute('use `{}`'.format(database))
            table_cursor.execute(query.format(table=table))
            for row in table_cursor:
                if self.field.search(row[0]):
                    field = row[1]
                    break
        print('{db}.{table}\t{field}'.format(db=database, table=table, field=field))


if __name__ == '__main__':
    HiveTablesMetadata().main()
