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

Processes Cloudera Navigator exported CSV logs to list the tables used (selected from)

This allows you to see if you wasting time maintaining datasets nobody is using

Handles more than naive filtering delimited column numbers which will miss many table and database names:

    1. table/database name fields are often blank and need to be inferred from SQL queries field
    2. SQL queries often contain newlines which break the rows up
    3. multi-line SQL queries with commented out lines are stripped to avoid false positives of what is being used

See cloudera_navigator_audit_download_logs.sh for a script to export these logs

./cloudera_navigator_tables_used.py navigator_audit_2019_hive.csv navigator_audit_2019_impala.csv \
                                    navigator_audit_2020_hive.csv navigator_audit_2020_impala.csv

Output - CSV format to stdout:

database,table

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
    from harisekhon.utils import CriticalError, log
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1.0'


class ClouderaNavigatorTablesUsed(CLI):

    def __init__(self):
        # Python 2.x
        super(ClouderaNavigatorTablesUsed, self).__init__()
        # Python 3.x
        # super().__init__()
        self.delimiter = None
        self.quotechar = None
        self.escapechar = None
        self.data = {}
        self.timeout_default = None

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

    def process_options(self):
        super(ClouderaNavigatorTablesUsed, self).process_options()
        self.delimiter = self.get_opt('delimiter')
        self.quotechar = self.get_opt('quotechar')
        self.escapechar = self.get_opt('escapechar')
        if not self.args:
            self.usage('no CSV file argument given')

    def run(self):
        quoting = csv.QUOTE_ALL
        if self.quotechar == '':
            quoting = csv.QUOTE_NONE

        fieldnames = ['database', 'table']
        csv_writer = csv.DictWriter(sys.stdout,
                                    delimiter=self.delimiter,
                                    quotechar=self.quotechar,
                                    escapechar=self.escapechar,
                                    quoting=quoting,
                                    fieldnames=fieldnames)
        for filename in self.args:
            self.process_file(filename)

        csv_writer.writeheader()
        for database in sorted(self.data):
            for table in sorted(self.data[database]):
                csv_writer.writerow({'database': database,
                                     'table': table})
        #if log.isEnabledFor(logging.DEBUG):
        #    sys.stdout.flush()

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

    # TODO: should really be refactored to be smaller simpler chunks of code
    # XXX: this post processing is ugly as hell and probably brittle - YMMV
    def process_file(self, filename):
        re_select_from_table = re.compile(r'\bselect\b.+\bfrom\b(?:\s|\n)+([^\s,]+)', re.I | re.MULTILINE | re.DOTALL)
        operations_to_ignore = [
            '',
            'HIVEREPLICATIONCOMMAND',
            'START',
            'STOP',
            'RESTART',
            'LOAD',
            'SWITCHDATABASE',
        ]
        with open(filename) as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',', quotechar='"', escapechar='\\')
            headers = csv_reader.next()
            len_headers = len(headers)
            # needed to ensure row joining works later on with number of fields left
            assert len_headers == 44
            operation_index = 4
            table_index = 19
            database_index = 21
            sql_index = 36
            assert headers[operation_index] == 'Operation'
            assert headers[table_index] == 'table_name'
            assert headers[database_index] == 'database_name'
            assert headers[sql_index] == 'Operation Text'
            partial_row = []
            sql_decomment = self.sql_decomment
            # more complicated than I wish it was - msg me if you know a simpler cleaner way
            for row in csv_reader:
                #log.debug('row = %s', row)
                #try:
                # various logic to handle rows broken on newlines inside SQL queries
                len_row = len(row)
                if len_row > len_headers:
                    #log.debug('collapsing fields in row: %s', row)
                    difference = len_row - len_headers
                    row[sql_index] = ','.join([sql_decomment(_) for _ in row[sql_index:difference]])
                    row = row[:sql_index] + row[sql_index + difference:]
                    len_row = len(row)
                    #log.debug('collapsed row: %s', row)
                #log.debug('row length: %s', len_row)
                #log.debug('partial row length: %s', len(partial_row))
                if len_row == len_headers:
                    pass
                elif len_row < len_headers:
                    log.debug('row (partial): %s', row)
                    if len_row + len(partial_row) == len_headers + 1:
                        #log.debug('length row + partial_row == header length, completing partial row')
                        #log.debug('partial_row = %s', partial_row)
                        #log.debug('row = %s', row)
                        # join first field to last field to complete SQL query
                        sql_fragment = sql_decomment(row[0])
                        partial_row[-1] = partial_row[-1] + r'\n ' + sql_fragment
                        partial_row += row[1:]
                        #log.debug('partial_row = %s', partial_row)
                    elif partial_row:
                        #log.debug('partial_row: %s', partial_row)
                        #log.debug('row: %s', row)
                        # join next fragment of SQL query to incomplete last item containing the first part of SQL query
                        partial_row[-1] = partial_row[-1] + r'\n ' + r'\n '.join(row)
                        #log.debug('accumulated partial row: %s', partial_row)
                    elif len(partial_row) > len_headers:
                        raise CriticalError('len(partial_row) > len_headers - {} > {} for partial row: {}'\
                                            .format(len(partial_row), len_headers, partial_row))
                    else:
                        partial_row = row
                    #log.debug('partial_row = %s', partial_row)
                    #log.debug('len partial row = %s', len(partial_row))
                    #log.debug('len headers = %s', len_headers)
                    if len(partial_row) == len_headers:
                        # process accumulated row as normal
                        row = partial_row
                        partial_row = []
                        #log.debug('accumulated completed row: %s', row)
                    else:
                        continue
                elif partial_row:
                    raise CriticalError('incompleted partial row: {}'.format(partial_row))
                len_row = len(row)
                if len_row != len_headers:
                    raise CriticalError('row items ({}) != header items ({}) for offending row: {}'\
                                        .format(len_row, len_headers, row))
                #log.debug(row)
                database = row[21]
                table = row[19]
                if not table.strip():
                    operation = row[4]
                    if operation == 'QUERY':
                        log.debug('table not found in row: %s', row)
                        query = row[36]
                        log.debug('trying to parse: %s', query)
                        match = re_select_from_table.search(query)
                        if match:
                            table = match.group(1)
                            if '.' in table:
                                (database, table) = table.split('.', 1)
                        else:
                            log.warning('failed to parse table from query: %s', query)
                    elif operation in operations_to_ignore:
                        continue
                    else:
                        log.debug('table not found in row and operation is not a query to parse: %s', row)
                if not table and not database:
                    continue
                table = table.lower()
                database = database.lower()
                self.data[database] = self.data.get(database, {})
                self.data[database][table] = 1
                #except IndexError as _:
#                    if log.isEnabledFor(logging.DEBUG):
#                        log.error('%s - offending line: %s', _, row)
#                    else:
                #    raise CriticalError('ERROR: %s - offending line: %s', _, row)

    @staticmethod
    def sql_decomment(string):
        return string.split('--')[0]


if __name__ == '__main__':
    ClouderaNavigatorTablesUsed().main()
