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

Connect to Impala or HiveServer2 and dump all the schemas, tables and columns out in CSV format to stdout

CSV format:

database,table,column,type


Tested on CDH 5.10, Hive 1.1.0 and Impala 2.7.0 with Kerberos

Due to a thrift / impyla bug this needs exactly thrift==0.9.3, see

https://github.com/cloudera/impyla/issues/286

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import logging
import os
import socket
import sys
from impala.dbapi import connect

__author__ = 'Hari Sekhon'
__version__ = '0.1.1'

logging.basicConfig()
log = logging.getLogger(os.path.basename(sys.argv[0]))

host_envs = [
    'HIVESERVER2_HOST',
    'HIVE_HOST',
    'IMPALA_HOST',
    'HOST'
]

port_envs = [
    'HIVESERVER2_PORT',
    'HIVE_PORT',
    'IMPALA_PORT',
    'PORT'
]

def getenvs(keys, default=None):
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default

def parse_args():
    parser = argparse.ArgumentParser(
        description="Dumps all Hive / Impala schemas, tables, columns and types to CSV format on stdout")
    parser.add_argument('-H', '--host', default=getenvs(host_envs, socket.getfqdn()),\
                        help='HiveServer2 / Impala host ' + \
                             '(default: fqdn of local host, $' + ', $'.join(host_envs) + ')')
    parser.add_argument('-P', '--port', type=int, default=getenvs(port_envs, 10000),
                        help='HiveServer2 / Impala port (default: 10000 if called as hive, ' + \
                                                                  '21050 if called as impala, $' + \
                                                                  ', $'.join(port_envs) + ')')
    parser.add_argument('-k', '--kerberos', action='store_true', help='Use Kerberos (you must kinit first)')
    parser.add_argument('-n', '--krb5-service-name', default='hive',
                        help='Service principal (default: \'hive\', or \'impala\' if called as impala_schemas_csv.py)')
    parser.add_argument('-S', '--ssl', action='store_true', help='Use SSL')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode')
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.INFO)

    if 'impala' in sys.argv[0]:
        if args.krb5_service_name == 'hive':
            log.info('called as impala, setting service principal to impala')
            args.krb5_service_name = 'impala'
        if args.port == 10000:
            log.info('called as impala, setting port to 21050')
            args.port = 21050
    return args

def connect_db(args, database):
    auth_mechanism = None
    if args.kerberos:
        auth_mechanism = 'GSSAPI'

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

    conn = connect_db(args, None)

    print('database,table,column,type')
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
                            print('{database},{table},{column},{type}'\
                                  .format(database=database,
                                          table=table,
                                          column=column,
                                          type=column_type))


if __name__ == '__main__':
    main()
