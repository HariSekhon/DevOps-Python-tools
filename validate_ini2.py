#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-09-15 15:29:39 +0200 (Fri, 15 Sep 2017)
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

More basic INI file Validator Tool using Python's native ConfigParser

See validate_ini.py for a better more flexible version

Validates each file passed as an argument

Directories are recursed, checking all files ending in a .ini suffix.

Works like a standard unix filter program - if no files are passed as arguments or '-' is given then reads
from standard input

See also the more flexible validate_ini.py

This version is less flexible to different format varieties:

Stricter in some ways - requires section headers
Looser in other ways - allows without any special switch:
                       - colon delimited ini files
                       - hash comments
                       - duplicate keys and sections
                       - blank files

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import sys
try:
    from ConfigParser import ConfigParser, Error as ConfigParserError
except ImportError:
    from configparser import ConfigParser, Error as ConfigParserError
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import ERRORS, log_option, validate_regex
    from validate_ini import IniValidatorTool
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.12.3'


class IniValidatorTool2(IniValidatorTool):

    def __init__(self):
        # Python 2.x
        super(IniValidatorTool2, self).__init__()
        # Python 3.x
        # super().__init__()
        self.re_suffix = re.compile(r'.*\.ini$', re.I)

    def add_options(self):
        self.add_opt('-p', '--print', action='store_true',
                     help='Print the INI lines(s) which are valid, else print nothing (useful for shell ' + \
                    'pipelines). Exit codes are still 0 for success, or {0} for failure'.format(ERRORS['CRITICAL']))
        self.add_opt('-i', '--include', metavar='regex', default=os.getenv('INCLUDE'),
                     help='Regex of file / directory paths to check only ones that match ($INCLUDE, case insensitive)')
        self.add_opt('-e', '--exclude', metavar='regex', default=os.getenv('EXCLUDE'),
                     help='Regex of file / directory paths to exclude from checking, ' + \
                          '($EXCLUDE, case insensitive, takes priority over --include)')

    def process_options(self):
        self.opts = {
            'print': self.get_opt('print')
        }
        self.include = self.get_opt('include')
        self.exclude = self.get_opt('exclude')
        if self.include:
            validate_regex(self.include, 'include')
            self.include = re.compile(self.include, re.I)
        if self.exclude:
            validate_regex(self.exclude, 'exclude')
            self.exclude = re.compile(self.exclude, re.I)
        for key in self.opts:
            log_option(key, self.opts[key])

    def process_ini(self, filehandle):
        config = ConfigParser()
        try:
            config.readfp(filehandle)
        except ConfigParserError as _:
            raise AssertionError(_)



if __name__ == '__main__':
    IniValidatorTool2().main()
