#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-03-16 19:21:24 +0000 (Mon, 16 Mar 2020)
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

Processes Cloudera Navigator CSV logs exported from PostgreSQL to list the tables used (SELECT'ed from)

This allows you to see if you're wasting time maintaining datasets nobody is using

See cloudera_navigator_audit_logs_export_postgres.sh for a script to export these logs

Supports reading directly from gzipped logs if they end in .gz file extension.
However, the gzip library may have issues around universal newline support, if so, gunzip first.

./cloudera_navigator_tables_used_postgres.py nav.public.hive_audit_events_*.csv.gz \\
                                             nav.public.impala_audit_events_*.csv.gz ...

Output is quoted CSV format to stdout (same as hive_schemas_csv.py for easier comparison):

"database","table"

Tested on Navigator logs for Hive/Impala on Cloudera Enterprise 5.10

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import csv
#import logging
import os
import re
import sys
srcdir = os.path.abspath(os.path.dirname(__file__))
pylib = os.path.join(srcdir, 'pylib')
lib = os.path.join(srcdir, 'lib')
sys.path.append(pylib)
sys.path.append(lib)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, isInt
    #from harisekhon import CLI
    from cloudera_navigator_tables_used import ClouderaNavigatorTablesUsed
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2.1'


class ClouderaNavigatorTablesUsedPostgreSQL(ClouderaNavigatorTablesUsed):

    def __init__(self):
        # Python 2.x
        super(ClouderaNavigatorTablesUsedPostgreSQL, self).__init__()
        # Python 3.x
        # super().__init__()
        # recombine records due to SQL \n breaking up records, new records start like:
        # 306529,1574163624392,1,hive,
        self.re_new_record = re.compile(r'^\d+,\d+,[01],(?:hive|impala),')
        # get db + table from resource path (just one layer of checks)
        self.re_resource = re.compile(r'/(\w+)\.db/(\w+)')

# Navigator table logs:
#
# gzcat nav.public.hive_audit_events_2019_11_19.csv.gz | csv_header_indices.sh
#      0  id
#      1  event_time
#      2  allowed
#      3  service_name
#      4  username
#      5  ip_addr
#      6  operation
#      7  database_name
#      8  object_type
#      9  table_name
#     10  operation_text
#     11  impersonator
#     12  resource_path
#     13  object_usage_type

# gzcat nav.public.impala_audit_events_2019_11_19.csv.gz | csv_header_indices.sh
#      0  id
#      1  event_time
#      2  allowed
#      3  service_name
#      4  username
#      5  impersonator
#      6  ip_addr
#      7  operation
#      8  query_id
#      9  session_id
#     10  status
#     11  database_name
#     12  object_type
#     13  table_name
#     14  privilege
#     15  operation_text

    def process_file(self, filehandle):
        csv_reader = csv.reader(filehandle, delimiter=',', quotechar='"', escapechar='\\')
        headers = csv_reader.next()
        self.len_headers = len(headers)
        # needed to ensure row joining works later on with number of fields left
        assert self.len_headers == 14 or self.len_headers == 16
        user_index = 4
        assert headers[user_index] == 'username'
        # Hive postgres audit log
        if self.len_headers == 14:
            operation_index = 6
            database_index = 7
            table_index = 9
            sql_index = 10
            resource_index = 12
            assert headers[resource_index] == 'resource_path'
        # Impala postgres audit log
        elif self.len_headers == 16:
            operation_index = 7
            database_index = 11
            table_index = 13
            sql_index = 15
            resource_index = None
        else:
            raise AssertionError('headers != 14 or 16 - unrecognized audit log - not Hive or Impala')
        assert headers[sql_index] == 'operation_text'
        assert headers[database_index] == 'database_name'
        assert headers[table_index] == 'table_name'
        assert headers[operation_index] == 'operation'
        self.indicies = {
            'user_index': user_index,
            'operation_index': operation_index,
            'resource_index': resource_index,
            'table_index': table_index,
            'database_index': database_index,
            'sql_index': sql_index,
        }
        self.process_rows(csv_reader)

    def is_new_record(self, current_row):
        return self.re_new_record.match(','.join(current_row))

    def parse_table(self, row):
        #log.debug(row)
        user = row[self.indicies['user_index']]
        # user: 'hari.sekhon'
        # kerberos principals: 'hari.sekhon@somedomain.com' or 'impala/fqdn@domain.com'
        if self.re_ignored_users and self.re_ignored_users.match(user):
            log.debug('skipping row for ignored user %s: %s', user, row)
            return (None, None)
        database = row[self.indicies['database_index']].strip()
        table = row[self.indicies['table_index']].strip()
        if not database or not table or not self.re_table.match('{}.{}'.format(database, table)):
            #log.info('table not found in fields for row: %s', row)
            operation = row[self.indicies['operation_index']]
            if operation in self.operations_to_ignore:
                return (None, None)
            elif operation == 'QUERY':
                query = row[self.indicies['sql_index']]
                # cheaper than re_ignore to pre-filter
                if query in ('GET_TABLES', 'GET_SCHEMAS', 'INVALIDATE METADATA'):
                    return (None, None)
                (database, table) = self.get_db_table_from_resource(row)
                if database and table:
                    pass
                else:
                    log.debug('database/table not found in row: %s', row)
                    log.debug('trying to parse: %s', query)
                    match = self.re_select_from_table.search(query)
                    if match:
                        table = match.group(1)
                        if '.' in table:
                            (database, table) = table.split('.', 1)
                    # could use .search but all these seem to be at beginning
                    elif self.re_ignore.match(query):
                        return (None, None)
                    else:
                        log.warning('failed to parse database/table from query: %s', query)
                        return (None, None)
            else:
                log.debug('database/table not found in row and operation is not a query to parse: %s', row)
                return (None, None)
        if not table and not database:
            return (None, None)
        if table:
            table = table.lower().strip('`')
            if ' ' in table:
                raise AssertionError('table \'{}\' has spaces - parsing error for row: {}'\
                                    .format(table, self.index_output(row)))
        if database:
            database = database.lower().strip('`')
            if ' ' in database:
                raise AssertionError('database \'{}\' has spaces - parsing error for row: {}'\
                                    .format(database, self.index_output(row)))
        if table == 'null':
            raise AssertionError('table == null - parsing error for row: {}'.format(row))
        return (database, table)

    def get_db_table_from_resource(self, row):
        # only available for hive audit logs, not impala
        if self.indicies['resource_index'] is None:
            return (None, None)
        database = None
        table = None
        resource = row[self.indicies['resource_index']]
        if resource:
            match = self.re_resource.search(resource)
            if match:
                database = match.group(1)
                table = match.group(2)
        return (database, table)

    def collapse_sql_fields(self, row):
        sql_index = self.indicies['sql_index']
        len_row = len(row)
        if len_row > self.len_headers:
            log.debug('collapsing fields in row: %s', row)
            difference = len_row - self.len_headers
            # slice indicies must be integers
            if not isInt(difference):
                raise AssertionError("difference in field length '{}' is not an integer for row: {}"\
                                    .format(difference, row))
            difference = int(difference)
            row[sql_index] = ','.join([self.sql_decomment(_) for _ in row[sql_index:difference]])
            row = row[:sql_index] + row[sql_index+difference:]
            log.debug('collapsed row: %s', row)
        else:
            log.debug('not collapsing row: %s', row)
        return row


if __name__ == '__main__':
    ClouderaNavigatorTablesUsedPostgreSQL().main()
