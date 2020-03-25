#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-09-12 13:44:24 +0200 (Mon, 12 Sep 2016)
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

# NOTE: 'flush' is not supported in Happybase as it's not in the Thrift API,
#       only available in the Java API, see HBaseAdmin.flush(table)

# I'll write a JVM native alternative to this later as I needed this quickly

"""

Tool to iterate on and flush all HBase tables

Written for flushing bulk imports skipping the WAL, for example OpenTSDB bulk import.

The Thrift API doesn't support this action so it uses the HBase shell locally which must be in the $PATH

There is also a shell script version of this in the adjacent DevOps-Perl-Tools repo

Tested on Hortonworks HDP 2.3 (HBase 1.1.2) and Apache HBase 1.0.3, 1.1.6, 1.2.1, 1.2.2, 1.3.1

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import logging
import os
import re
import sys
import traceback
import subprocess
PIPE = subprocess.PIPE
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, die, autoflush
    from harisekhon.utils import validate_regex
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'


class HBaseFlushTables(CLI):

    def __init__(self):
        # Python 2.x
        super(HBaseFlushTables, self).__init__()
        # Python 3.x
        # super().__init__()
        self.table_list_header_regex = re.compile('TABLE')
        self.table_list_end_regex = re.compile(r'row.*\sin\s.*\sseconds')
        self.table_regex = None
        self.timeout_default = 6 * 3600
        autoflush()

    def add_options(self):
        self.add_opt('-r', '--regex', help='Regex of tables to flush')
        self.add_opt('-l', '--list-tables', action='store_true', help='List tables and exit')

    def process_args(self):
        log.setLevel(logging.INFO)
        self.no_args()
        regex = self.get_opt('regex')
        if regex:
            validate_regex(regex)
            self.table_regex = re.compile(regex, re.I)
            log.info('filtering to flush only tables matching regex \'{0}\''.format(regex))

    def get_tables(self):
        log.info('getting table list')
        try:
            process = subprocess.Popen(['hbase', 'shell'], stdin=PIPE, stdout=PIPE, stderr=subprocess.STDOUT)
            (stdout, _) = process.communicate('list')
            process.wait()
            if process.returncode != 0:
                print('ERROR:', end='')
                die(stdout)
            lines = stdout.split('\n')
            lineno = 1
            for line in lines:
                if self.table_list_header_regex.search(line):
                    break
                lineno += 1
            if lineno > len(lines):
                die("Failed to parse table list output (couldn't find the starting line TABLE)")
            tables = set()
            for line in lines[lineno:]:
                if self.table_list_end_regex.search(line):
                    break
                line = line.strip()
                if not line:
                    continue
                tables.add(line)
            return tables
        except OSError as _:
            die("OSError running hbase shell to list tables: {0}".format(_))
        except subprocess.CalledProcessError as _:
            print('Failed to get tables using HBase shell:\n')
            print(_.output)
            sys.exit(_.returncode)

    def run(self):
        tables = self.get_tables()
        if not tables:
            die('No Tables Found')
        if self.get_opt('list_tables'):
            print('Tables:\n\n' + '\n'.join(tables))
            sys.exit(3)
        tables_to_flush = set()
        if self.table_regex:
            log.info('filtering tables based on regex')
            for table in sorted(list(tables)):
                if self.table_regex.search(table):
                    tables_to_flush.add(table)
        else:
            tables_to_flush = sorted(list(tables))
        if log.isEnabledFor(logging.INFO):
            log.info('Flushing tables:\n\n%s\n', '\n'.join(tables_to_flush))
        flush_commands = '\n'.join(["flush '{0}'".format(table) for table in tables_to_flush])
        try:
            # by having stdout and stderr go to the same place more likely the output will be in a sane order
            process = subprocess.Popen(['hbase', 'shell'], stdin=PIPE, stdout=PIPE, stderr=subprocess.STDOUT)
            (stdout, _) = process.communicate(input=flush_commands)
            process.wait()
            if process.returncode != 0:
                print('ERROR:', end='')
                die(stdout)
            print(stdout)
        except OSError as _:
            die("OSError running hbase shell to flush tables: {0}".format(_))
        except subprocess.CalledProcessError as _:
            print('Failed to get tables using HBase shell:\n')
            print(_.output)
            sys.exit(_.returncode)


if __name__ == '__main__':
    HBaseFlushTables().main()
