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
#  http://www.linkedin.com/in/harisekhon
#

"""

Tool to show the first and last N lines. Works like a standard unix filter program for all files passed as arguments
or if no files are given the it applies to standard input.

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
    from harisekhon.utils import *      # pylint: disable=wrong-import-position,wildcard-import
    from harisekhon import CLI          # pylint: disable=wrong-import-position
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'

class HeadTail(CLI):

    def __init__(self):
        # Python 2.x
        super(HeadTail, self).__init__()
        # Python 3.x
        # super().__init__()
        self.num_lines = 10
        self.sep = '=' * 20

    def add_options(self):
        self.parser.add_option('-n', '--num', metavar='number_of_lines',
                               type=int,
                               default=self.num_lines,
                               help='Number of lines to show (default: 10)')

    def run(self):
        self.num_lines = self.options.num
        if not self.args:
            self.args.append('-')
        for arg in self.args:
            if arg == '-':
                continue
            if not os.path.exists(arg):
                print("'%s' not found" % arg)
                sys.exit(ERRORS['WARNING'])
            if os.path.isfile(arg):
                vlog_option('file', arg)
            elif os.path.isdir(arg):
                vlog_option('directory', arg)
            else:
                die("path '%s' could not be determined as either a file or directory" % arg)
        for filename in self.args:
            if filename == '-':
                self.headtail(sys.stdin.read())
            else:
                with open(filename) as self.f:
                    self.headtail(self.f.read())

    def headtail(self, content):
        lines = content.split(os.linesep)
        print(os.linesep.join(lines[:self.num_lines]))
        print(lines[:self.num_lines])
        print(self.sep)
        print(os.linesep.join(lines[-self.num_lines:]))


if __name__ == '__main__':
    HeadTail().main()
