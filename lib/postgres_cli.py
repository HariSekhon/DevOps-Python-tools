#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-03-12 17:39:57 +0000 (Thu, 12 Mar 2020)
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import socket
import sys
import psycopg2
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, validate_host, validate_port, validate_user, validate_password
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1.0'


class PostgreSQLCLI(CLI):

    def __init__(self):
        # Python 2.x
        super(PostgreSQLCLI, self).__init__()
        # Python 3.x
        # super().__init__()
        self.name = ['PostgreSQL', 'Postgres', 'PG']
        self.host = None
        self.port = None
        self.default_host = socket.getfqdn()
        self.default_port = 5432
        self.user = None
        self.password = None
        #self.ssl = False
        self.verbose_default = 1
        self.timeout_default = None

    def add_options(self):
        super(PostgreSQLCLI, self).add_options()
        self.add_hostoption()
        self.add_useroption()
        self.add_opt('-d', '--database', help='Database to connect to')

    def process_options(self):
        super(PostgreSQLCLI, self).process_options()
        self.host = self.get_opt('host')
        self.host = self.get_opt('host')
        self.user = self.get_opt('user')
        self.password = self.get_opt('password')
        validate_host(self.host)
        validate_port(self.port)
        validate_user(self.user)
        validate_password(self.password)
        self.port = int(self.port)
        #self.ssl = self.get_opt('ssl')

    def connect(self, database):
        log.info('connecting to %s:%s database %s as user %s', self.host, self.port, database)
        return psycopg2.connect(host=self.host,
                                port=self.port,
                                database=database,
                                user=self.user,
                                password=self.password)
