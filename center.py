#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#  args: -s <<< "Auth & Config"
#  args: -s <<< "GKE Clusters"
#
#  Author: Hari Sekhon
#  Date: 2016-01-29 21:05:38 +0000 (Fri, 29 Jan 2016)
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

Tool to re-center text args or text from standard input to a given width
while ignoring the leading comment char such as the common unix # symbol

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import os
import re
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import isChars, log_option
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.4.2'

class Center(CLI):

    def __init__(self):
        # Python 2.x
        super(Center, self).__init__()
        # Python 3.x
        # super().__init__()
        # this doesn't put enough spaces around ampersands, eg. in "Auth & Config"
        #self.re_bound = re.compile(r'(\b)')
        self.re_spaces = re.compile(r'(\s)')
        self.re_chars = re.compile(r'([^\s])(?!\s)')
        self.timeout_default = None

    def add_options(self):
        self.add_opt('-w', '--width', default=80, type='int', metavar='<num_chars>',
                     help='Target line width to center for in chars')
        self.add_opt('-n', '--no-comment', action='store_true',
                     help='No comment prefix handling')
        self.add_opt('-s', '--space', action='store_true', default=False,
                     help='Space all chars out, makes bigger headings')

    def run(self):
        log_option('width', self.get_opt('width'))
        log_option('no comment prefix', self.get_opt('no_comment'))
        log_option('space chars', self.get_opt('space'))
        if self.args:
            self.process_line(' '.join(self.args))
        else:
            for line in sys.stdin:
                self.process_line(line)

    def space(self, line):
        #line = self.re_bound.sub(r' ', line)
        line = self.re_spaces.sub(r'\1\1\1', line)
        line = self.re_chars.sub(r'\1 ', line)
        return line

    def process_line(self, line):
        char = ''
        if not line:
            return
        if not self.get_opt('no_comment'):
            char = ' '
            # preliminary strip() to be able to pick up # if it isn't the first char and their are spaces before it
            line = line.strip()
            if isChars(line[0], '#'):
                char = line[0]
                line = line.lstrip(char)
            elif len(line) > 1 and isChars(line[0:1], '/'):
                char = '//'
                line = line.lstrip(char)
            elif len(line) > 1 and isChars(line[0:1], '-'):
                char = '--'
                line = line.lstrip(char)
        if self.get_opt('space'):
            line = self.space(line)
        line = line.strip()
        side = int(max((self.get_opt('width') - len(line)) / 2, 0))
        print(char + ' ' * side + line)

if __name__ == '__main__':
    Center().main()
