#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-07 22:57:18 +0000 (Thu, 07 Jan 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish # pylint: disable=line-too-long
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to show the first and last N lines. Works like a standard unix filter program for all files passed as arguments
or if no files are given then it applies to standard input.

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
    from harisekhon.utils import die, ERRORS, log_option
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2.1'

class HeadTail(CLI):

    def __init__(self):
        # Python 2.x
        super(HeadTail, self).__init__()
        # Python 3.x
        # super().__init__()
        self.num_lines = 10
        self.sep = '...'
        self.docsep = '=' * 80
        self.quiet = False

    def add_options(self):
        #self.timeout_default = 300
        self.add_opt('-n', '--num', metavar='number_of_lines',
                     type=int, default=self.num_lines,
                     help='Number of lines to show (default: 10)')
        self.add_opt('-q', '--quiet', action='store_true',
                     default=False, help="Don't print separators in output")

    def run(self):
        self.num_lines = self.get_opt('num')
        log_option('number of lines', self.num_lines)
        self.quiet = self.get_opt('quiet')
        log_option('quiet', self.quiet)
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
                self.headtail(sys.stdin.read())
            else:
                with open(filename) as _:
                    self.headtail(_.read())
            if not self.quiet and len(self.args) > 1:
                print(self.docsep)

    def headtail(self, content):
        lines = content.split(os.linesep)
        print(os.linesep.join(lines[:self.num_lines]))
        if not self.quiet:
            print(self.sep)
        print(os.linesep.join(lines[-self.num_lines:]).rstrip(os.linesep))


if __name__ == '__main__':
    HeadTail().main()
