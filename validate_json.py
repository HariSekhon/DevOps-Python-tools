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
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

JSON Validator Tool

Validates each file passed as an argument

Directories if given are detected and recursed, checking all files in the directory tree ending in a .json suffix.

First tries each file contents as a whole json document, if that fails validation or catches a memory error, then
it assumes the file contains Big Data / MongoDB data with one json document per line and tries independent
validation of each line as a separate json document.

Works like a standard unix filter program - if no files are passed as arguments or '-' is passed then reads from
standard input (--multi-line must be specified explicitly if feeding to stdin as can't rewind the standard input
stream to test for multi-line on a second pass).

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# from __future__ import unicode_literals

import os
import re
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import isJson, die, ERRORS, vlog_option, uniq_list_ordered
    from harisekhon.utils import log
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.8.0'

class JsonValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(JsonValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.iostream = None
        self.re_json_suffix = re.compile(r'.*\.json$', re.I)
        # these msgs get reset with the correct filename in check_file further down()
        self.valid_json_msg = '<UNKNOWN_FILENAME> => JSON OK'
        self.invalid_json_msg = '<UNKNOWN_FILENAME> => JSON INVALID'
        single_quotes = '(found single quotes not double quotes)'
        self.valid_json_msg_single_quotes = '%s %s' % (self.valid_json_msg, single_quotes)
        self.invalid_json_msg_single_quotes = '%s %s' % (self.invalid_json_msg, single_quotes)
        self.permit_single_quotes = False
        self.passthru = False
        # self.multi_record_detected = False
        # self.single_quotes_detected = False
        self.msg = None
        self.failed = False

    def add_options(self):
        self.add_opt('-m', '--multi-record', action='store_true',
                     help='Test explicitly for multi-record JSON data, where each line is a separate json ' \
                     + 'document separated by newlines. Must use if reading multi-record json format ' \
                     + 'on standard input')
        self.add_opt('-p', '--print', dest='passthru', action='store_true',
                     help='Print the JSON document(s) if valid (passthrough), else print nothing (useful for shell ' +
                     'pipelines). Exit codes are still 0 for success, or %s for failure'
                     % ERRORS['CRITICAL'])
        self.add_opt('-s', '--permit-single-quotes', dest='permit_single_quotes', action='store_true',
                     help='Accept single quotes as valid (JSON standard requires double quotes but some' +
                     ' systems like MongoDB are ok with single quotes)')

    def check_multirecord_json(self):
        log.debug('check_multirecord_json()')
        for line in self.iostream:
            if isJson(line):
                # can't use self.print() here, don't want to print valid for every line of a file / stdin
                if self.passthru:
                    print(line, end='')
            elif isJson(line.replace("'", '"')):
                if self.permit_single_quotes:
                    log.debug('valid multirecord json (single quoted)')
                    # self.single_quotes_detected = True
                    if self.passthru:
                        print(line, end='')
                else:
                    log.debug('invalid multirecord json (single quoted)')
                    self.failed = True
                    if not self.passthru:
                        die('%s (multi-record format)' % self.invalid_json_msg_single_quotes)
                    return False
            else:
                log.debug('invalid multirecord json')
                self.failed = True
                return False
        # self.multi_record_detected = True
        log.debug('multirecord json (all lines passed)')
        if not self.passthru:
            print('%s (multi-record format)' % self.valid_json_msg)
        return True

    def print(self, content):
        if self.passthru:
            print(content, end='')
        else:
            print(self.msg)

    def check_json(self, content):
        log.debug('check_json()')
        if isJson(content):
            log.debug('valid json')
            self.msg = self.valid_json_msg
            self.print(content)
        # XXX: Limitation this may not work with JSON with double quotes embedded within single quotes as
        # that may lead to unbalanced quoting, although that is still a data problem so might be ok for it to be flagged
        # as failing
        elif isJson(content.replace("'", '"')):
            log.debug('valid json (single quotes)')
            # self.single_quotes_detectedsingle_quotes_detected = True
            if self.permit_single_quotes:
                self.msg = self.valid_json_msg_single_quotes
                self.print(content)
            else:
                self.failed = True
                self.msg = self.invalid_json_msg_single_quotes
                if not self.passthru:
                    die(self.msg)
        else:
            log.debug('not valid json')
            if self.iostream is not sys.stdin:
                self.iostream.seek(0)
                if self.check_multirecord_json():
                    return True
            # pointless since it would simply return 'ValueError: No JSON object could be decoded'
            # if self.verbose > 2:
            #     try:
            #         json.loads(content)
            #     except Exception, e:
            #         print(e)
            else:
                self.failed = True
                self.msg = self.invalid_json_msg
                if not self.passthru:
                    die(self.msg)

    # looks like this does a .read() anyway, not buying any efficiency enhancement
    #
    #  usage:
    # self.check_json_fp(self.iostream)
    # must reset afterwards, otherwise next check will result in Invalid JSON due to blank
    # self.iostream.seek(0)
    #
    # def check_json_fp(self, fp):
    #     try:
    #         json.load(fp)
    #         return True
    #     except ValueError:
    #         die(self.invalid_json_msg)

    def run(self):
        self.permit_single_quotes = self.get_opt('permit_single_quotes')
        self.passthru = self.get_opt('passthru')
        if not self.args:
            self.args.append('-')
        args = uniq_list_ordered(self.args)
        for arg in args:
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
        for arg in args:
            self.check_path(arg)
        if self.failed:
            sys.exit(ERRORS['CRITICAL'])

    def check_path(self, path):
        if path == '-' or os.path.isfile(path):
            self.check_file(path)
        elif os.path.isdir(path):
            for item in os.listdir(path):
                subpath = os.path.join(path, item)
                if os.path.isdir(subpath):
                    self.check_path(subpath)
                elif self.re_json_suffix.match(item):
                    self.check_file(subpath)
        else:
            die("failed to determine if path '%s' is file or directory" % path)

    def check_file(self, filename):
        if filename == '-':
            filename = '<STDIN>'
        self.valid_json_msg = '%s => JSON OK' % filename
        self.invalid_json_msg = '%s => JSON INVALID' % filename
        single_quotes = '(found single quotes not double quotes)'
        self.valid_json_msg_single_quotes = '%s %s' % (self.valid_json_msg, single_quotes)
        self.invalid_json_msg_single_quotes = '%s %s' % (self.invalid_json_msg, single_quotes)
        mem_err = "file '%s', assuming Big Data multi-record json and re-trying validation line-by-line" % filename
        if filename == '<STDIN>':
            self.iostream = sys.stdin
            if self.get_opt('multi_record'):
                if not self.check_multirecord_json():
                    self.failed = True
                    self.msg = self.invalid_json_msg
                    if not self.passthru:
                        die(self.msg)
            else:
                self.check_json(sys.stdin.read())
        else:
            try:
                with open(filename) as self.iostream:
                    if self.get_opt('multi_record'):
                        self.check_multirecord_json()
                    else:
                        # most JSON files are fine to slurp like this
                        # Big Data / MongoDB JSON data files are json multi-record and can be large
                        # may throw exception after running out of RAM in which case try handling line-by-line
                        # (json document-per-line)
                        try:
                            content = self.iostream.read()
                            try:
                                self.check_json(content)
                            except MemoryError:
                                print("memory error validating contents from %s" % mem_err)
                                self.iostream.seek(0)
                                self.check_multirecord_json()
                        except MemoryError:
                            print("memory error reading %s" % mem_err)
                            self.iostream.seek(0)
                            self.check_multirecord_json()
            except IOError as _:
                die("ERROR: %s" % _)
        if self.failed:
            sys.exit(2)


if __name__ == '__main__':
    JsonValidatorTool().main()
