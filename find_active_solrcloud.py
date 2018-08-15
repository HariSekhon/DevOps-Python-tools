#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: Tue Sep  5 10:49:49 CEST 2017
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

Tool to return first available SolrCloud node from an argument list of hosts

Can mix and match between a comma separated list of hosts (--host server1,server2 or contents of the $HOST
environment variable if not specified) and general free-form space separated arguments, which is useful if piping
a host list through xargs.

Multi-threaded for speed and exits upon first available host response to minimize delay to ~ 1 second or less.

Useful for simplying scripting or generically extending tools that only take a single --host option but want to query
cluster status from any node (eg. check_elasticsearch_cluster_status.pl from Advanced Nagios Plugins Collection)

By default checks the same --port on all servers. Hosts may have optional :<port> suffixes added to individually
override each one.

Exits with return code 1 and NO_AVAILABLE_SERVER if none of the namenodes are active, --quiet mode will not print
NO_AVAILABLE_SERVER.

Tested on SolrCloud 4.10 5.5 6.0 6.1 6.2 6.3 6.4 6.5 6.6

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import os
import sys
import traceback
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from find_active_server import FindActiveServer
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.7.0'


class FindActiveSolrCloud(FindActiveServer):

    def __init__(self):
        # Python 2.x
        super(FindActiveSolrCloud, self).__init__()
        # Python 3.x
        # super().__init__()
        self.default_port = 3389
        self.url_path = '/solr/'
        self.protocol = 'http'
        self.regex = r'Solr\s+Admin'

    def add_options(self):
        self.add_hostoption(name='Solr', default_port=self.default_port)
        self.add_ssl_opt()
        self.add_common_opts()

    def process_options(self):
        self.validate_common_opts()


if __name__ == '__main__':
    FindActiveSolrCloud().main()
