#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-05-10 11:26:49 +0100 (Tue, 10 May 2016)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help improve this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to show Docker tags for one or more docker repos from a Docker Registry

Written for convenience as Docker CLI doesn't currently support this:

See https://github.com/docker/docker/issues/17238

Will strip docker image tag suffix from args for convenience

See also dockerhub_show_tags.py

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
    from harisekhon.utils import log_option, validate_host, validate_port, validate_user, validate_password
    from dockerhub_show_tags import DockerHubTags
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.5.1'


class DockerRegistryTags(DockerHubTags):

    def __init__(self):
        # Python 2.x
        super(DockerRegistryTags, self).__init__()
        # Python 3.x
        # super().__init__()
        self.url_base = None
        self.protocol = 'http'
        self.user = None
        self.password = None

    def add_options(self):
        self.add_hostoption(name='Docker Registry', default_port=5000)
        self.add_useroption(name='Docker Registry')
        self.add_ssl_option()
        self.add_opt('-q', '--quiet', action='store_true', default=False,
                     help='Output only the tags, one per line (useful for shell scripting)')

    def process_options(self):
        host = self.get_opt('host')
        port = self.get_opt('port')
        self.user = self.get_opt('user')
        self.password = self.get_opt('password')
        validate_host(host)
        validate_port(port)
        if self.user is not None:
            validate_user(self.user)
        if self.password is not None:
            validate_password(self.password)
        if self.get_opt('ssl'):
            log_option('ssl', 'True')
            self.protocol = 'https'
        self.url_base = '{protocol}://{host}:{port}/v2'.format(protocol=self.protocol,
                                                               host=host,
                                                               port=port)

if __name__ == '__main__':
    DockerRegistryTags().main()
