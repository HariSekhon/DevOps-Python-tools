#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-01-02 17:08:32 +0000 (Thu, 02 Jan 2020)
#
#  https://github.com/HariSekhon/DevOps-Python-tools
#
#  License: GNU GPL version 2 (this file only), rest of this repo is licensed as per the adjacent LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/HariSekhon
#

"""

Tool to anonymize hex input but keeping the structure of the positions of numbers and digits

Useful to retain the structure of ID formats

Reads any given files or standard input and replaces each hex character with an incrementing number of letter (a-f)
printing to stdout for piping or redirecting to a file as per unix filter command standards

Works like a standard unix filter program - if no files are passed as arguments or '-' is passed then reads from
standard input

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
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1.0'


class HexAnonymize(CLI):

    def __init__(self):
        # Python 2.x
        super(HexAnonymize, self).__init__()
        # Python 3.x
        # super().__init__()
        self.preserve_case = False
        self.only_hex_alphas = False

    def add_options(self):
        super(HexAnonymize, self).add_options()
        self.add_opt('-c', '--case', action='store_true', help='Preserve case')
        self.add_opt('-o', '--hex-only', action='store_true',
                     help='Only replace hex alpha chars (A-F, a-f), otherwise replaces all alphanumerics for safety')

    def process_options(self):
        super(HexAnonymize, self).process_options()
        self.preserve_case = self.get_opt('case')
        self.only_hex_alphas = self.get_opt('hex_only')

    def hexanonymize(self, filehandle):
        preserve_case = self.preserve_case
        only_hex_alphas = self.only_hex_alphas
        hex_alphas = ['a', 'b', 'c', 'd', 'e', 'f']
        for line in filehandle:
            integer = 1
            letter = 'a'
            for char in line:
                if char.isdigit():
                    char = integer
                    integer += 1
                    if integer > 9:
                        integer = 0
                elif (not only_hex_alphas and char.isalpha()) or char.lower() in hex_alphas:
                    if preserve_case and char.isupper():
                        char = letter.upper()
                    else:
                        char = letter
                    letter = chr(ord(char) + 1)
                    if letter.lower() not in hex_alphas:
                        letter = 'a'
                print(char, end='')


    def run(self):
        if not self.args:
            self.args.append('-')
        for arg in self.args:
            if arg == '-':
                continue
            if not os.path.exists(arg):
                print("'%s' not found" % arg)
                sys.exit(1)
        for arg in self.args:
            if arg == '-':
                self.hexanonymize(sys.stdin)
            else:
                with open(arg) as filehandle:
                    self.hexanonymize(filehandle)


if __name__ == '__main__':
    HexAnonymize().main()
