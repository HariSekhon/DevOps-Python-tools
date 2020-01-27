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

Connect to a HiveServer2 or Impala daemon and dump all the schemas, tables and columns out in CSV format to stdout

In practice Hive is much more reliable for dumping masses of schema

Impala appears faster initially but then slows down more than Hive and hits things query handle errors
under sustained load of extracting large amounts of schema information

There is also a risk that Impala's metadata may be out of date, so Hive is strongly preferred for this


CSV format:

database,table,column,type


I recommend generating quoted csv because you may encounter Hive data types such as decimal(15,2)
which would cause incorrect field splitting, you can disable by setting --quotechar='' to blank but
if escaping is needed then you will be forced to specify an --escapechar otherwise the csv writer will
raise a traceback to tell you to set one (eg. --escapechar='\\')

Tested on CDH 5.10, Hive 1.1.0 and Impala 2.7.0 with Kerberos

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
import socket
import sys
from impala.dbapi import connect
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, validate_host, validate_port
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.4.0'


class HiveSchemasCSV(CLI):

    def __init__(self):
        # Python 2.x
        super(HiveSchemasCSV, self).__init__()
        # Python 3.x
        # super().__init__()
        self.name = ['HiveServer2', 'Hive']
        self.host = None
        self.port = None
        self.default_host = socket.getfqdn()
        self.default_port = 10000
        self.default_service_name = 'hive'
        self.kerberos = False
        self.krb5_service_name = self.default_service_name
        self.ssl = False
        self.delimiter = None
        self.quotechar = None
        self.escapechar = None

        if 'impala' in sys.argv[0]:
            self.name = 'Impala'
            self.default_port = 21050
            self.default_service_name = 'impala'
            self.env_prefixes = ['IMPALA']

    def add_options(self):
        super(HiveSchemasCSV, self).add_options()
        self.add_hostoption()
        self.add_opt('-k', '--kerberos', action='store_true', help='Use Kerberos (you must kinit first)')
        self.add_opt('-n', '--krb5-service-name', default=self.default_service_name,
                     help='Service principal (default: {})'.format(self.default_service_name))
        self.add_opt('-S', '--ssl', action='store_true', help='Use SSL')
        # must set type to str otherwise csv module gives this error on Python 2.7:
        # TypeError: "delimiter" must be string, not unicode
        # type=str worked with argparse but when integrated with CLI then 'from __future__ import unicode_literals'
        # breaks this - might break in Python 3 if the impyla module doesn't fix behaviour
        self.add_opt('-d', '--delimiter', default=',', type=str, help='Delimiter to use (default: ,)')
        self.add_opt('-Q', '--quotechar', default='"', type=str,
                     help='Generate quoted CSV (recommended, default is double quote \'"\')')
        self.add_opt('-E', '--escapechar', help='Escape char if needed')

    def process_options(self):
        super(HiveSchemasCSV, self).process_options()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        validate_host(self.host)
        validate_port(self.port)
        self.port = int(self.port)
        self.kerberos = self.get_opt('kerberos')
        self.krb5_service_name = self.get_opt('krb5_service_name')
        self.ssl = self.get_opt('ssl')
        self.delimiter = self.get_opt('delimiter')
        self.quotechar = self.get_opt('quotechar')
        self.escapechar = self.get_opt('escapechar')

    def connect(self, database):
        auth_mechanism = None
        if self.kerberos:
            auth_mechanism = 'GSSAPI'
            log.debug('kerberos enabled')
            log.debug('krb5 remote service principal name = %s', self.krb5_service_name)
        if self.ssl:
            log.debug('ssl enabled')

        log.info('connecting to %s:%s database %s', self.host, self.port, database)
        return connect(
            host=self.host,
            port=self.port,
            auth_mechanism=auth_mechanism,
            use_ssl=self.ssl,
            #user=user,
            #password=password,
            database=database,
            kerberos_service_name=self.krb5_service_name
            )

    def run(self):

        conn = self.connect('default')

        quoting = csv.QUOTE_ALL
        if self.quotechar == '':
            quoting = csv.QUOTE_NONE
        fieldnames = ['database', 'table', 'column', 'type']
        csv_writer = csv.DictWriter(sys.stdout,
                                    delimiter=self.delimiter,
                                    quotechar=self.quotechar,
                                    escapechar=self.escapechar,
                                    quoting=quoting,
                                    fieldnames=fieldnames)
        csv_writer.writeheader()
        log.info('querying databases')
        with conn.cursor() as db_cursor:
            db_cursor.execute('show databases')
            for db_row in db_cursor:
                database = db_row[0]
                log.info('querying tables for database %s', database)
                #db_conn = connect_db(args, database)
                #with db_conn.cursor() as table_cursor:
                with conn.cursor() as table_cursor:
                    # doesn't support parameterized query quoting from dbapi spec
                    #table_cursor.execute('use %(database)s', {'database': database})
                    table_cursor.execute('use {}'.format(database))
                    table_cursor.execute('show tables')
                    for table_row in table_cursor:
                        table = table_row[0]
                        log.info('describing table %s', table)
                        with conn.cursor() as column_cursor:
                            # doesn't support parameterized query quoting from dbapi spec
                            #column_cursor.execute('use %(database)s', {'database': database})
                            #column_cursor.execute('describe %(table)s', {'table': table})
                            column_cursor.execute('use {}'.format(database))
                            column_cursor.execute('describe {}'.format(table))
                            for column_row in column_cursor:
                                column = column_row[0]
                                column_type = column_row[1]
                                csv_writer.writerow({'database': database,
                                                     'table': table,
                                                     'column': column,
                                                     'type': column_type})


if __name__ == '__main__':
    HiveSchemasCSV().main()
