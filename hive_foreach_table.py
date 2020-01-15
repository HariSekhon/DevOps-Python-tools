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

Tool to connect to a HiveServer2 / Impala node and execute a query for all tables in all databases,
or only those matching given db / table regexes

Useful for getting row counts of all tables or analyzing tables:

eg.

hive_foreach_table.py --query 'SELECT COUNT(*) FROM {db}.{table}'
hive_foreach_table.py --query 'ANALYZE TABLE {db}.{table} COMPUTE STATS'

impala_foreach_table.py --query 'SELECT COUNT(*) FROM {db}.{table}'
impala_foreach_table.py --query 'COMPUTE STATS {table}'

or just for today's partition:

hive_foreach_table.py --query "ANALYZE TABLE {db}.{table} PARTITION(date=$(date '+%Y-%m-%d')) COMPUTE STATS"

impala_foreach_table.py --query "COMPUTE INCREMENTAL STATS {db}.{table} PARTITION(date=$(date '+%Y-%m-%d'))"


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
import logging
import os
import re
import socket
import sys
import impala
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
    parser = argparse.ArgumentParser(description="Executes a SQL statement for each matching {} table".format(name))
    parser.add_argument('-H', '--host', default=getenvs(host_envs, socket.getfqdn()),\
                        help='{} host '.format(name) + \
                             '(default: fqdn of local host, $' + ', $'.join(host_envs) + ')')
    parser.add_argument('-P', '--port', type=int, default=getenvs(port_envs, default_port),
                        help='{} port (default: {}, '.format(name, default_port) + \
                                                                  ', $'.join(port_envs) + ')')
    parser.add_argument('-q', '--query', required=True, help='Query or statement to execute for each table' + \
            ' (replaces {db} and {table} in the query string with each table and its database)')
    parser.add_argument('-d', '--database', default='.*', help='Database regex (default: .*)')
    parser.add_argument('-t', '--table', default='.*', help='Table regex (default: .*)')
    parser.add_argument('-k', '--kerberos', action='store_true', help='Use Kerberos (you must kinit first)')
    parser.add_argument('-n', '--krb5-service-name', default=default_service_name,
                        help='Service principal (default: {})'.format(default_service_name))
    parser.add_argument('-S', '--ssl', action='store_true', help='Use SSL')
#
# ignore tables that fail with errors like:
#
# Hive (CDH has MR, no tez):
#
# impala.error.OperationalError: Error while processing statement: FAILED: Execution Error, return code 1 from org.apache.hadoop.hive.ql.exec.mr.MapRedTask  # pylint: disable=line-too-long
#
# Impala:
#
# impala.error.HiveServer2Error: AnalysisException: Unsupported type 'void' in column '<column>' of table '<table>'
# CAUSED BY: TableLoadingException: Unsupported type 'void' in column '<column>' of table '<table>'
#
    parser.add_argument('-e', '--ignore-errors', action='store_true', help='Ignore errors and continue')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode')
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

    try:
        database_regex = re.compile(args.database, re.I)
        table_regex = re.compile(args.table, re.I)
    except re.error as _:
        log.error('error in provided regex: %s', _)
        sys.exit(3)

    conn = connect_db(args, 'default')

    log.info('querying databases')
    with conn.cursor() as db_cursor:
        db_cursor.execute('show databases')
        for db_row in db_cursor:
            database = db_row[0]
            if not database_regex.search(database):
                log.debug("skipping database '%s', does not match regex '%s'", database, args.database)
                continue
            log.info('querying tables for database %s', database)
            #db_conn = connect_db(args, database)
            #with db_conn.cursor() as table_cursor:
            with conn.cursor() as table_cursor:
                try:
                    # doesn't support parameterized query quoting from dbapi spec
                    #table_cursor.execute('use %(database)s', {'database': database})
                    table_cursor.execute('use {}'.format(database))
                    table_cursor.execute('show tables')
                except impala.error.HiveServer2Error as _:
                    log.error(_)
                    if 'AuthorizationException' in str(_):
                        continue
                    raise
                for table_row in table_cursor:
                    table = table_row[0]
                    if not table_regex.search(table):
                        log.debug("skipping database '%s' table '%s', does not match regex '%s'", \
                                  database, table, args.table)
                        continue
                    try:
                        query = args.query.format(db=database, table=table)
                    except KeyError as _:
                        if _ == 'db':
                            query = args.query.format(table=table)
                    try:
                        execute(conn, database, table, query)
                    except Exception as _:
                        if args.ignore_errors:
                            log.error("database '%s' table '%s':  %s", database, table, _)
                            continue
                        raise

def execute(conn, database, table, query):
    try:
        log.info(" %s.%s - running %s", database, table, query)
        with conn.cursor() as query_cursor:
            # doesn't support parameterized query quoting from dbapi spec
            query_cursor.execute(query)
            for result in query_cursor:
                print('{db}.{table}\t{result}'.format(db=database, table=table, \
                                                      result='\t'.join([str(_) for _ in result])))
    #except (impala.error.OperationalError, impala.error.HiveServer2Error) as _:
    #    log.error(_)
    except impala.error.ProgrammingError as _:
        log.error(_)
        # COMPUTE STATS returns no results
        if 'Trying to fetch results on an operation with no results' not in str(_):
            raise


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Control-C", file=sys.stderr)
