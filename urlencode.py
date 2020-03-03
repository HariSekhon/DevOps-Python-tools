#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-03-03 17:34:06 +0000 (Tue, 03 Mar 2020)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to url encode text from standard input or a text argument

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import os
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon import CLI
    from harisekhon.utils import isPythonMinVersion
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

# pylint: disable=no-name-in-module,import-error
if isPythonMinVersion(3):
    from urllib.parse import quote
else:
    from urllib import quote

__author__ = 'Hari Sekhon'
__version__ = '0.1.0'

class URLEncode(CLI):

    def run(self):
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                self.encode(arg)
        else:
            for line in sys.stdin:
                line = line.rstrip('\n').rstrip('\r')
                self.encode(line)

    @staticmethod
    def encode(string):
        #print(urllib.parse.quote(string))
        print(quote(string))

if __name__ == '__main__':
    URLEncode().main()
