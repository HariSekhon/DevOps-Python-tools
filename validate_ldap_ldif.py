#!/usr/bin/env python
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-08-04 00:53:10 +0200 (Fri, 04 Aug 2017)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

LDAP LDIF Validator Tool

Validates each LDAP Interchange Format file passed as an argument

Directories if given are detected and recursed, checking all files in the directory tree ending in a .ldif suffix.

Works like a standard unix filter program - if no files are passed as arguments or '-' is passed then reads from
standard input

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import sys
import traceback
#from pprint import pprint
#from pprint import pformat
try:
    from ldif3 import LDIFParser
except ImportError:
    print(traceback.format_exc(), end='')
    sys.exit(4)
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, log_option, uniq_list_ordered, validate_regex
    from harisekhon.utils import log
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6'


class LdifValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(LdifValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.re_ldif_suffix = re.compile(r'.*\.ldif$', re.I)
        # these msgs get reset with the correct filename in check_file further down()
        self.valid_ldif_msg = '<UNKNOWN_FILENAME> => LDIF OK'
        self.invalid_ldif_msg = '<UNKNOWN_FILENAME> => LDIF INVALID'
        self.passthru = False
        self.msg = None
        self.failed = False
        self.exclude = None

    def add_options(self):
        self.add_opt('-p', '--print', dest='passthru', action='store_true',
                     help='Print the LDIF document(s) if valid (passthrough), else print nothing (useful for shell ' +
                     'pipelines). Exit codes are still 0 for success, or %s for failure'
                     % ERRORS['CRITICAL'])
        self.add_opt('-e', '--exclude', metavar='regex', default=os.getenv('exclude'),
                     help='regex of file / directory paths to exclude from checking ($exclude)')

    def process_options(self):
        self.exclude = self.get_opt('exclude')
        if self.exclude:
            validate_regex(self.exclude, 'exclude')
            self.exclude = re.compile(self.exclude, re.I)

    def is_excluded(self, path):
        if self.exclude and self.exclude.search(path):
            log.debug("excluding path: %s", path)
            return True
        return False

    def print(self, filehandle):
        if self.passthru:
            # TODO: this works but theoretically it shouldn't and might be working off buffers for small sample files
            #       consider changing this to collect and write to a temporary file and testing that instead
            filehandle.seek(0)
            print(filehandle.read(), end='')
        else:
            print(self.msg)

    @staticmethod
    def is_invalid_ldif(filehandle):
        try:
            parser = LDIFParser(filehandle)
            # returns a generator so step through to force processing and trigger exception
            for _dn, entry in parser.parse():
                log.debug('got entry record: %s', _dn)
                # looks the same
                #log.debug('%s', pformat(entry))
                log.debug('%s', entry)
            log.debug('%s records read', parser.records_read)
            if not parser.records_read:
                raise ValueError('no records read')
            return False
        except ValueError as _:
            log.debug('ValueError: %s', _)
            return _

    def check_ldif(self, filehandle):
        #log.debug('check_ldif()')
        exception = self.is_invalid_ldif(filehandle)
        if exception:
            log.debug('invalid ldif')
            self.failed = True
            self.msg = self.invalid_ldif_msg
            if not self.passthru:
                die(self.msg)
        else:
            log.debug('valid ldif')
            self.msg = self.valid_ldif_msg
            self.print(filehandle)

    def run(self):
        self.passthru = self.get_opt('passthru')
        if not self.args:
            self.args.append('-')
        args = uniq_list_ordered(self.args)
        for arg in args:
            if arg == '-':
                continue
            if not os.path.exists(arg):
                print("'{0}' not found".format(arg))
                sys.exit(ERRORS['CRITICAL'])
            if os.path.isfile(arg):
                log_option('file', arg)
            elif os.path.isdir(arg):
                log_option('directory', os.path.abspath(arg))
            else:
                die("path '%s' could not be determined as either a file or directory" % arg)
        for arg in args:
            self.check_path(arg)
        if self.failed:
            sys.exit(ERRORS['CRITICAL'])

    def check_path(self, path):
        if path == '-' or os.path.isfile(path):
            self.check_file(path)
        elif os.path.isdir(path):
            self.walk(path)
        else:
            die("failed to determine if path '%s' is file or directory" % path)

    # don't need to recurse when using walk generator
    def walk(self, path):
        if self.is_excluded(path):
            return
        for root, dirs, files in os.walk(path, topdown=True):
            # modify dirs in place to prune descent for increased efficiency
            # requires topdown=True
            # calling is_excluded() on joined root/dir so that things like
            #   '/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+' will match
            dirs[:] = [d for d in dirs if not self.is_excluded(os.path.join(root, d))]
            for filename in files:
                file_path = os.path.join(root, filename)
                if self.re_ldif_suffix.match(file_path):
                    self.check_file(file_path)

    def check_file(self, filename):
        if filename == '-':
            filename = '<STDIN>'
        self.valid_ldif_msg = '%s => LDIF OK' % filename
        self.invalid_ldif_msg = '%s => LDIF INVALID' % filename
        if filename == '<STDIN>':
            log.debug('checking <STDIN>')
            #self.check_ldif(sys.stdin.read())
            self.check_ldif(sys.stdin)
        else:
            if self.is_excluded(filename):
                return
            try:
                log.debug("checking '%s'", filename)
                with open(filename, 'rb') as iostream:
                    #content = iostream.read()
                    #self.check_ldif(content)
                    self.check_ldif(iostream)
            except IOError as _:
                die("ERROR: %s" % _)
        if self.failed:
            sys.exit(2)


if __name__ == '__main__':
    LdifValidatorTool().main()
