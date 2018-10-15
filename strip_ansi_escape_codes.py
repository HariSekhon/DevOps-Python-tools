#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-09-09 23:06:06 +0100 (Sun, 09 Sep 2018)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish # pylint: disable=line-too-long
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Strip ANSI Escape Codes from Text String input

Works as a standard unix filter program, reading from file arguments or standard input and printing to standard output

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, log_option, strip_ansi_escape_codes
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2'


# pylint: disable=too-few-public-methods

class StripAnsiEscapeCodes(CLI):

#    def __init__(self):
#        # Python 2.x
#        super(StripAnsiEscapeCodes, self).__init__()
#        # Python 3.x
#        # super().__init__()

    def run(self):
        if not self.args:
            self.args.append('-')
        for arg in self.args:
            if arg == '-':
                continue
            if not os.path.exists(arg):
                print("'%s' not found" % arg)
                sys.exit(ERRORS['WARNING'])
            if os.path.isfile(arg):
                log_option('file', arg)
            elif os.path.isdir(arg):
                log_option('directory', arg)
            else:
                die("path '%s' could not be determined as either a file or directory" % arg)
        for filename in self.args:
            if filename == '-':
                for line in sys.stdin:
                    print(strip_ansi_escape_codes(line), end='')
            else:
                with open(filename) as filehandle:
                    for line in filehandle:
                        print(strip_ansi_escape_codes(line), end='')


if __name__ == '__main__':
    StripAnsiEscapeCodes().main()
