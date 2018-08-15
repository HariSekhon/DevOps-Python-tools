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

Tool to show Docker tags for one or more Quay.io repos

Written for convenience as Docker CLI doesn't currently support this:

See https://github.com/docker/docker/issues/17238

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
    from dockerhub_show_tags import DockerHubTags
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.2'


class QuayTags(DockerHubTags):

    def __init__(self):
        # Python 2.x
        super(QuayTags, self).__init__()
        # Python 3.x
        # super().__init__()
        self.url_base = 'http://quay.io/v2'

    def run(self):
        if not self.args:
            self.usage('no repos given as args')
        self.quiet = self.get_opt('quiet')
        if not self.quiet:
            print('\nQuay.io ', end='')
        for arg in self.args:
            self.print_tags(arg)


if __name__ == '__main__':
    QuayTags().main()
