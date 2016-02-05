#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-29 21:05:38 +0000 (Fri, 29 Jan 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

"""

Tool to re-center text args or text from standard input to a given width
while ignoring the leading comment char such as the common unix # symbol

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
    from harisekhon.utils import isChars
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2.1'

class Center(CLI):

    def add_options(self):
        self.add_opt('-w', '--width', default=80, type='int', metavar='<num_chars>',
                     help='Target line width to center for in chars')
        self.add_opt('-n', '--no-comment', action='store_true',
                     help='No comment prefix handling')

    def run(self):
        if self.args:
            self.process_line(' '.join(self.args))
        else:
            for line in sys.stdin:
                self.process_line(line)

    def process_line(self, line):
        char = ''
        if not line:
            return
        if not self.options.no_comment:
            char = ' '
            # preliminary strip() to be able to pick up # if it isn't the first char and their are spaces before it
            line = line.strip()
            if isChars(line[0], '#'):
                char = line[0]
                line = line.lstrip(char)
            elif len(line) > 1 and isChars(line[0:1], '/'):
                char = '//'
                line = line.lstrip(char)
        line = line.strip()
        side = int(max((self.options.width - len(line)) / 2, 0))
        print(char + ' ' * side + line)

if __name__ == '__main__':
    Center().main()
