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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

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
__version__ = '0.5.0'


class HiveImpalaCLI(CLI):

    def __init__(self):
        # Python 2.x
        super(HiveImpalaCLI, self).__init__()
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
        self.verbose_default = 1
        #self.timeout_default = 86400
        self.timeout_default = None
        if 'impala' in sys.argv[0]:
            self.name = 'Impala'
            self.default_port = 21050
            self.default_service_name = 'impala'

    def add_options(self):
        super(HiveImpalaCLI, self).add_options()
        self.add_hostoption()
        self.add_opt('-k', '--kerberos', action='store_true', help='Use Kerberos (you must kinit first)')
        self.add_opt('-n', '--krb5-service-name', default=self.default_service_name,
                     help='Service principal (default: {})'.format(self.default_service_name))
        self.add_opt('-S', '--ssl', action='store_true', help='Use SSL')

    def process_options(self):
        super(HiveImpalaCLI, self).process_options()
        self.host = self.get_opt('host')
        self.port = self.get_opt('port')
        validate_host(self.host)
        validate_port(self.port)
        self.port = int(self.port)
        self.kerberos = self.get_opt('kerberos')
        self.krb5_service_name = self.get_opt('krb5_service_name')
        self.ssl = self.get_opt('ssl')

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
