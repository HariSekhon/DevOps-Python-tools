#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-12-22 23:25:25 +0000 (Tue, 22 Dec 2015)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

"""
JSON Validator Tool

Does a simple validation of each file passed as an argument to this script.
"""


from __future__ import print_function

__author__  = 'Hari Sekhon'
__version__ = '0.1'

import os
import sys
# using optparse rather than argparse for servers still on Python 2.6
sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])) + '/pylib')
try:
    from harisekhon.utils import *
    from harisekhon import CLI
except ImportError, e:
    print('module import failed: %s' % e, file=sys.stderr)
    sys.exit(4)

class JsonValidatorTool(CLI):

    def run(self):
        if not self.args:
            self.usage()
        for filename in self.args:
            validate_file(filename)
        for filename in self.args:
            with open(filename) as f:
                if isJson(f.read()):
                    print('%s => JSON OK' % filename)
                else:
                    die('%s => INVALID JSON' % filename)


if __name__ == '__main__':
    JsonValidatorTool().main()
