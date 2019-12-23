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
from __future__ import unicode_literals

import argparse
import csv
import logging
import os
import socket
import sys
from impala.dbapi import connect

__author__ = 'Hari Sekhon'
__version__ = '0.3.0'

logging.basicConfig()
log = logging.getLogger(os.path.basename(sys.argv[0]))

def getenvs(keys, default=None):
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default

def parse_args():
    name = 'HiveServer2'
    default_port = 10000
    default_service_name = 'hive'
    host_envs = [
        'HIVESERVER2_HOST',
        'HIVE_HOST',
        'HOST'
    ]
    port_envs = [
        'HIVESERVER2_PORT',
        'HIVE_PORT',
        'PORT'
    ]

    if 'impala' in sys.argv[0]:
        name = 'Impala'
        default_port = 21050
        default_service_name = 'impala'
        host_envs = [
            'IMPALA_HOST',
            'HOST'
        ]
        port_envs = [
            'IMPALA_PORT',
            'PORT'
        ]
    parser = argparse.ArgumentParser(
        description="Dumps all {} schemas, tables, columns and types to CSV format on stdout".format(name))
    parser.add_argument('-H', '--host', default=getenvs(host_envs, socket.getfqdn()),\
                        help='{} host '.format(name) + \
                             '(default: fqdn of local host, $' + ', $'.join(host_envs) + ')')
    parser.add_argument('-P', '--port', type=int, default=getenvs(port_envs, default_port),
                        help='{} port (default: {}, '.format(name, default_port) + \
                                                                  ', $'.join(port_envs) + ')')
    parser.add_argument('-k', '--kerberos', action='store_true', help='Use Kerberos (you must kinit first)')
    parser.add_argument('-n', '--krb5-service-name', default=default_service_name,
                        help='Service principal (default: {})'.format(default_service_name))
    parser.add_argument('-S', '--ssl', action='store_true', help='Use SSL')
    # must set type to str otherwise csv module gives this error on Python 2.7:
    # TypeError: "delimiter" must be string, not unicode
    parser.add_argument('-d', '--delimiter', default=',', type=str, help='Delimiter to use (default: ,)')
    parser.add_argument('-Q', '--quotechar', default='"', type=str,
                        help='Generate quoted CSV (recommended, default is double quote \'"\')')
    parser.add_argument('-E', '--escapechar', help='Escape char if needed')
    parser.add_argument('-v', '--verbose', action='count', help='Verbose mode')
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.INFO)
    if args.verbose > 1 or os.getenv('DEBUG'):
        log.setLevel(logging.DEBUG)

    return args

def connect_db(args, database):
    auth_mechanism = None
    if args.kerberos:
        auth_mechanism = 'GSSAPI'
        log.debug('kerberos enabled')
        log.debug('krb5 remote service principal name = %s', args.krb5_service_name)
    if args.ssl is True:
        log.debug('ssl enabled')

    log.info('connecting to %s:%s database %s', args.host, args.port, database)
    return connect(
        host=args.host,
        port=args.port,
        auth_mechanism=auth_mechanism,
        use_ssl=args.ssl,
        #user=user,
        #password=password,
        database=database,
        kerberos_service_name=args.krb5_service_name
        )

def main():
    args = parse_args()

    conn = connect_db(args, 'default')

    quoting = csv.QUOTE_ALL
    if args.quotechar == '':
        quoting = csv.QUOTE_NONE
    fieldnames = ['database', 'table', 'column', 'type']
    csv_writer = csv.DictWriter(sys.stdout,
                                delimiter=args.delimiter,
                                quotechar=args.quotechar,
                                escapechar=args.escapechar,
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
    try:
        main()
    except KeyboardInterrupt:
        print("Control-C", file=sys.stderr)
