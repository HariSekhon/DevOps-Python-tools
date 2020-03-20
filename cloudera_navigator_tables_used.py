#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-03-09 11:35:47 +0000 (Mon, 09 Mar 2020)
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

Processes Cloudera Navigator API exported CSV logs to list the tables used (SELECT'ed from)

This allows you to see if you're wasting time maintaining datasets nobody is using

Handles more than naive filtering delimited column numbers which will miss many table and database names:

    1. table/database name fields are often blank and need to be inferred from SQL queries field
       (currently limited to 'SELECT ... FROM ...' because JOINs are often complicated by use of table aliases)
    2. SQL queries often contain newlines which break the rows up - these are recombined in to single records
    3. multi-line SQL queries have comments stripped out to avoid false positives of what is being used
    4. where table/database field aren't available, also checks if inferrable from resource field
       to determine database and table name before parsing SQL which is a last resort
    5. optionally ignore selected users by regex
       - matches user or kerberos principal
       - eg. to omit ETL service account from skewing data access results

Supports reading directly from gzipped logs if they end in .gz file extension.
However, the gzip library may have issues around universal newline support, if so, gunzip first.

See cloudera_navigator_audit_logs_download.sh for a script to export these logs

./cloudera_navigator_tables_used.py navigator_audit_2019_hive.csv navigator_audit_2019_impala.csv \\
                                    navigator_audit_2020_hive.csv navigator_audit_2020_impala.csv

Output is quoted CSV format to stdout (same as hive_schemas_csv.py for easier comparison):

"database","table"

Tested on Navigator logs for Hive/Impala on Cloudera Enterprise 5.10
(but may require ongoing tweaks depending on quirks in your data set or changes in the API / logs)

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import csv
import gzip
import logging
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
    from harisekhon.utils import log, validate_regex, isInt, isPythonMinVersion
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.3.0'


class ClouderaNavigatorTablesUsed(CLI):

    def __init__(self):
        # Python 2.x
        super(ClouderaNavigatorTablesUsed, self).__init__()
        # Python 3.x
        # super().__init__()
        csv.field_size_limit(sys.maxsize)
        self.delimiter = None
        self.quotechar = None
        self.escapechar = None
        self.timeout_default = None
        #self.data = {}
        self.indicies = {}
        self.len_headers = None
        self.table_regex = r'[\w\.`]+'
        self.re_table = re.compile(self.table_regex)
        # doesn't handle JOINs because SQL pros usually use table aliases
        self.re_select_from_table = re.compile(r'\bSELECT\b.+\bFROM\b(?:\s|\n)+({table_regex})'\
                                               .format(table_regex=self.table_regex), \
                                               re.I | re.MULTILINE | re.DOTALL)
        ignore_statements = [
            'SHOW',
            'DESCRIBE',
            'USE',
            'CREATE',
            'DROP',
            'INSERT',
            'DELETE',
            'UPDATE',
            'GET_TABLES',
            'GET_SCHEMAS',
            'VIEW_METADATA',
            'ANALYZE',
            r'COMPUTE\s+STATS',
            'REFRESH',
            r'INVALIDATE\s+METADATA',
        ]
        self.re_ignore = re.compile(r'^\s*\b(?:' + '|'.join(ignore_statements) + r')\b',\
                                    re.I | re.MULTILINE | re.DOTALL)
        # 2020-01-31T20:45:59.000Z
        self.re_timestamp = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
        self.re_ignored_users = None
        self.csv_writer = None
        self.operations_to_ignore = [
            '',
            'HIVEREPLICATIONCOMMAND',
            'START',
            'STOP',
            'RESTART',
            'LOAD',
            'SWITCHDATABASE',
            'USE',
        ]

    def add_options(self):
        super(ClouderaNavigatorTablesUsed, self).add_options()
        # must set type to str otherwise csv module gives this error on Python 2.7:
        # TypeError: "delimiter" must be string, not unicode
        # type=str worked with argparse but when integrated with CLI then 'from __future__ import unicode_literals'
        # breaks this - might break in Python 3 if the impyla module doesn't fix behaviour
        self.add_opt('-d', '--delimiter', default=',', type=str, help='Delimiter to use for outputting (default: ,)')
        self.add_opt('-Q', '--quotechar', default='"', type=str,
                     help='Generate quoted CSV output (recommended, default is double quote \'"\')')
        self.add_opt('-E', '--escapechar', help='Escape char if needed (for both reading and writing)')
        self.add_opt('-i', '--ignore-users', help='Users to ignore, comma separated regex values')

    def process_options(self):
        super(ClouderaNavigatorTablesUsed, self).process_options()
        self.delimiter = self.get_opt('delimiter')
        self.quotechar = self.get_opt('quotechar')
        self.escapechar = self.get_opt('escapechar')
        ignore_users = self.get_opt('ignore_users')
        if ignore_users:
            ignored_users = ignore_users.split(',')
            for username in ignored_users:
                validate_regex(username, 'ignored user')
            # account for kerberized names - user, user@domain.com or user/host@domain.com
            self.re_ignored_users = re.compile('^(?:' + '|'.join(ignored_users) + ')(?:[@/]|$)', re.I)
        if not self.args:
            self.usage('no CSV file argument given')

    def run(self):
        quoting = csv.QUOTE_ALL
        if self.quotechar == '':
            quoting = csv.QUOTE_NONE

        #fieldnames = ['database', 'table', 'user']
        fieldnames = ['database', 'table']
        self.csv_writer = csv.DictWriter(sys.stdout,
                                         delimiter=self.delimiter,
                                         quotechar=self.quotechar,
                                         escapechar=self.escapechar,
                                         quoting=quoting,
                                         fieldnames=fieldnames)
        mode = 'rtU'
        if isPythonMinVersion(3):
            mode = 'rt'
        # open(..., encoding="utf-8") is Python 3 only - uses system default otherwise
        for filename in self.args:
            if filename.endswith('.gz'):
                log.debug("processing gzip'd file: %s", filename)
                with gzip.open(filename, mode) as filehandle:
                    self.process_file(filehandle)
            else:
                log.debug("processing file: %s", filename)
                with open(filename, mode) as filehandle:
                    self.process_file(filehandle)

        #csv_writer.writeheader()
        #for database in sorted(self.data):
        #    for table in sorted(self.data[database]):
        #        csv_writer.writerow({'database': database,
        #                             'table': table})
        #if log.isEnabledFor(logging.DEBUG):
        #    sys.stdout.flush()

# Navigator API Audit log output is a mess with duplicate columns and different naming conventions,
# eg. identical SQL in fields 18 and 36
#     table and database names in fields 19+21 vs 40+41
#     all duplicates with different header names
#
#  # same result for navigator_audit_2019_impala.csv
#  csv_header_indices.sh navigator_audit_2019_hive.csv
#      0  Timestamp
#      1  Username
#      2  "IP Address"
#      3  "Service Name"
#      4  Operation
#      5  Resource
#      6  Allowed
#      7  Impersonator
#      8  sub_operation
#      9  entity_id
#     10  stored_object_name
#     11  additional_info
#     12  collection_name
#     13  solr_version
#     14  operation_params
#     15  service
#     16  operation_text
#     17  url
#     18  operation_text
#     19  table_name
#     20  resource_path
#     21  database_name
#     22  object_type
#     23  Source
#     24  Destination
#     25  Permissions
#     26  "Delegation Token ID"
#     27  "Table Name"
#     28  Family
#     29  Qualifier
#     30  "Operation Text"
#     31  "Database Name"
#     32  "Table Name"
#     33  "Object Type"
#     34  "Resource Path"
#     35  "Usage Type"
#     36  "Operation Text"
#     37  "Query ID"
#     38  "Session ID"
#     39  Status
#     40  "Database Name"
#     41  "Table Name"
#     42  "Object Type"
#     43  Privilege

    def process_file(self, filehandle):
        csv_reader = csv.reader(filehandle, delimiter=',', quotechar='"', escapechar='\\')
        try:
            # Python 2
            headers = csv_reader.next()
        except AttributeError:
            # Python 3
            headers = next(csv_reader)
        self.len_headers = len(headers)
        # needed to ensure row joining works later on with number of fields left
        assert self.len_headers == 44
        user_index = 1
        operation_index = 4
        resource_index = 5
        object_index = 22  # used by collapse_sql_fields to check if SQL was split, do not change to index 33!
        # --
        # with massive queries taking the latter 2 is more likely to succeed,
        # possibly because there is a rare and subtle issue in collapse_sql_fields
        #table_index = 19
        #database_index = 21
        # or
        table_index = 41
        database_index = 40
        # --
        # fields 18 and 36 are identical SQL - need both to collapse rows later
        sql_index = 18
        sql_index2 = 36
        #assert headers[table_index] == 'table_name'  # index 19
        #assert headers[database_index] == 'database_name'  # index 21
        assert headers[table_index] == 'Table Name'  # index 41
        assert headers[database_index] == 'Database Name'  # index 40
        assert headers[user_index] == 'Username'
        assert headers[operation_index] == 'Operation'
        assert headers[resource_index] == 'Resource'
        assert headers[sql_index] == 'operation_text'
        assert headers[sql_index2] == 'Operation Text'
        assert headers[object_index] == 'object_type'
        self.indicies = {
            'user_index': user_index,
            'operation_index': operation_index,
            'resource_index': resource_index,
            'table_index': table_index,
            'database_index': database_index,
            'sql_index': sql_index,
            'sql_index2': sql_index2,  # needed for collapsing rows inflated by SQL fragmentation
            'object_index': object_index
        }
        self.process_rows(csv_reader)

    # logic to reconstruct rows because the Navigator API breaks the record format
    # with newlines in SQL coming out literally and fragmenting the records
    def process_rows(self, csv_reader):
        last_row = []
        for current_row in csv_reader:
            #log.debug('current row = %s', current_row)
            if not current_row:
                continue
            if self.is_new_record(current_row):
                row = last_row
                last_row = current_row
            else:
                last_row += current_row
                continue
            if not row:
                continue
            self.process_row(row)
        self.process_row(last_row)

    # originally did this by counting fields but SQL fragmentation generates extra fields
    def is_new_record(self, current_row):
        return self.re_timestamp.match(current_row[0])

    def process_row(self, row):
        if not row:
            return
        log.debug('processing row = %s', row)
        len_row = len(row)
        log.debug('row len = %s', len_row)
        if len_row > self.len_headers:
            row = self.collapse_sql_fields(row=row)
        len_row = len(row)
        if len_row != self.len_headers:
            raise AssertionError('row items ({}) != header items ({}) for offending row: {}'\
                                .format(len_row, self.len_headers, row))
        (database, table) = self.parse_table(row)
        self.output(row=row, database=database, table=table)

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
        database = None
        table = None
        resource = row[self.indicies['resource_index']]
        if resource and \
           ':' in resource and \
           'null:null' not in resource:
            # database:table in Resource field
            (database, table) = resource.split(':', 1)
        return (database, table)

    def output(self, row, database, table):
        if not self.re_table.match('{}.{}'.format(database, table)):
            log.warning('%s.%s does not match table regex', database, table)
            return
        # instead of collecting in ram, now just post-process through sort -u
        # this way it is easier to see live extractions, --debug and correlate
        #self.data[database] = self.data.get(database, {})
        #self.data[database][table] = 1
        if table and not database:
            log.info('got table but not database for row: %s', row)
        if database and not table:
            log.info('got database but not table for row: %s', row)
        if not table and not database:
            return
        #self.csv_writer.writerow({'database': database, 'table': table, 'user': row[self.indicies['user_index']]})
        self.csv_writer.writerow({'database': database, 'table': table})
        if log.isEnabledFor(logging.DEBUG):
            sys.stdout.flush()

    def collapse_sql_fields(self, row):
        sql_index = self.indicies['sql_index']
        sql_index2 = self.indicies['sql_index2']
        object_index = self.indicies['object_index']
        len_row = len(row)
        if len_row > self.len_headers:
            log.debug('collapsing fields in row: %s', row)
            # divide by 2 to account for this having been done twice in duplicated SQL operational text
            # Update: appears this broke as only 2nd occurence of SQL operational text field got split to new fields,
            # which is weird because the log shows both 1st and 2nd SQL text fields were double quoted
            difference = len_row - self.len_headers
            # seems first occurrence doesn't get split in some occurence,
            # wasn't related to open in newline universal mode though
            # if 2 fields after isn't the /user/hive/warehouse/blah.db then 1st SQL wasn't split
            # would have to regex /user/hive/warehouse/blah.db(?:/table)?
            #if not row[sql_index+2].endswith('.db'):
            # if object field is TABLE or DATABASE then 1st sql field wasn't split
            if row[object_index] not in ('TABLE', 'DATABASE'):
                difference /= 2
                # slice indicies must be integers
                if not isInt(difference):
                    raise AssertionError("difference in field length '{}' is not an integer for row: {}"\
                                        .format(difference, row))
                difference = int(difference)
                row[sql_index] = ','.join([self.sql_decomment(_) for _ in row[sql_index:difference]])
                row = row[:sql_index] + row[sql_index+difference:]
            row[sql_index2] = ','.join([self.sql_decomment(_) for _ in row[sql_index2:difference]])
            row = row[:sql_index2] + row[sql_index2+difference:]
            log.debug('collapsed row: %s', row)
        else:
            log.debug('not collapsing row: %s', row)
        return row

    @staticmethod
    def sql_decomment(string):
        return string.split('--')[0].strip()

    @staticmethod
    def index_output(obj):
        return '\n'.join(['{}\t{}'.format(index, item) for (index, item) in enumerate(obj)])


if __name__ == '__main__':
    ClouderaNavigatorTablesUsed().main()
