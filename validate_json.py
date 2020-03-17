#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-12-22 23:25:25 +0000 (Tue, 22 Dec 2015)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help improve or steer this or other code I publish
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

Even supports 'single quoted JSON' which while isn't technically valid is used by some systems like MongoDB and will
work with single quoted json with embedded double quotes even if the double quotes are not escaped.

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
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import isJson, die, ERRORS, log_option, uniq_list_ordered, validate_regex
    from harisekhon.utils import log
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.11.2'


class JsonValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(JsonValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.iostream = None
        self.re_json_suffix = re.compile(r'.*\.json$', re.I)
        self.filename = None
        self.valid_json_msg = ' => JSON OK'
        self.invalid_json_msg = ' => JSON INVALID'
        single_quotes = 'single quoted'
        self.valid_json_msg_single_quotes = '{0} ({1})'.format(self.valid_json_msg, single_quotes)
        self.valid_json_msg_single_quotes2 = '{0} ({1}, double quotes not escaped)'\
                                             .format(self.valid_json_msg, single_quotes)
        self.invalid_json_msg_single_quotes = '{0} ({1})'.format(self.invalid_json_msg, single_quotes)
        self.permit_single_quotes = False
        self.passthru = False
        # self.multi_record_detected = False
        # self.single_quotes_detected = False
        self.msg = None
        self.failed = False
        self.exclude = None

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
        self.add_opt('-e', '--exclude', metavar='regex', default=os.getenv('EXCLUDE'),
                     help='Regex of file / directory paths to exclude from checking ($EXCLUDE)')

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

    def check_multirecord_json(self):
        log.debug('check_multirecord_json()')
        normal_json = False
        single_quoted = False
        count = 0
        for line in self.iostream:
            if isJson(line):
                normal_json = True
                # can't use self.print() here, don't want to print valid for every line of a file / stdin
                if self.passthru:
                    print(line, end='')
                count += 1
                continue
            elif self.permit_single_quotes and self.check_json_line_single_quoted(line):
                single_quoted = True
                if self.passthru:
                    print(line, end='')
                count += 1
                continue
            else:
                log.debug('invalid multirecord json')
                self.failed = True
                if not self.passthru:
                    die(self.invalid_json_msg)
                return False
        if count == 0:
            log.debug('blank input, detected zero lines while multirecord checking')
            self.failed = True
            return False
        # self.multi_record_detected = True
        log.debug('multirecord json (all %s lines passed)', count)
        extra_info = ''
        if single_quoted:
            extra_info = ' single quoted'
            if normal_json:
                extra_info += ' mixed with normal json!'
                log.warning('mixture of normal and single quoted json detected, ' + \
                            'may cause issues for data processing engines')
        if not self.passthru:
            print('{0} (multi-record format{1}, {2} records)'.format(self.valid_json_msg, extra_info, count))
        return True

    def check_json_line_single_quoted(self, line):
        json_single_quoted = self.convert_single_quoted(line)
        if isJson(json_single_quoted):
            #log.debug('valid multirecord json (single quoted)')
            return True
        json_single_quoted_escaped = self.convert_single_quoted_escaped(line)
        if isJson(json_single_quoted_escaped):
            #log.debug('valid multirecord json (single quoted escaped)')
            return True
        return False

    def print(self, content):
        if self.passthru:
            print(content, end='')
        else:
            # intentionally concatenating so it'll blow up if self.filename is still set to None
            print(self.filename + self.msg)

    @staticmethod
    def convert_single_quoted(content):
        return content.replace("'", '"')

    def convert_single_quoted_escaped(self, content):
        return self.convert_single_quoted(content.replace('"', r'\"'))

    def check_json(self, content):
        log.debug('check_json()')
        if isJson(content):
            log.debug('valid json')
            self.msg = self.valid_json_msg
            self.print(content)
        # check if it's regular single quoted JSON a la MongoDB
        elif self.permit_single_quotes:
            log.debug('checking for single quoted JSON')
            json_single_quoted = self.convert_single_quoted(content)
            if isJson(json_single_quoted):
                # self.single_quotes_detected = True
                log.debug('valid json (single quotes)')
                self.msg = self.valid_json_msg_single_quotes
                self.print(content)
                return True
            log.debug('single quoted JSON check failed, trying with pre-escaping double quotes')
            # check if it's single quoted JSON with double quotes that aren't escaped,
            # by pre-escaping them before converting single quotes to doubles for processing
            json_single_quoted_escaped = self.convert_single_quoted_escaped(content)
            if isJson(json_single_quoted_escaped):
                #log.debug("found single quoted json with non-escaped double quotes in '%s'", filename)
                self.msg = self.valid_json_msg_single_quotes2
                self.print(content)
                return True
            log.debug('single quoted JSON check failed even with pre-escaping any double quotes')
            if self.rewind_check_multirecord_json():
                return True
            self.failed = True
            if not self.passthru:
                die(self.invalid_json_msg_single_quotes)
        else:
            log.debug('not valid json')
            if self.rewind_check_multirecord_json():
                return True
            # pointless since it would simply return 'ValueError: No JSON object could be decoded'
            # if self.verbose > 2:
            #     try:
            #         json.loads(content)
            #     except Exception as _:
            #         print(_)
            self.failed = True
            if not self.passthru:
                die(self.invalid_json_msg)
        return False

    def rewind_check_multirecord_json(self):
        if self.iostream is not sys.stdin:
            self.iostream.seek(0)
            if self.check_multirecord_json():
                return True
        return False

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
            self.check(path)
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
                if self.re_json_suffix.match(file_path):
                    self.check(file_path)

    def check(self, filename):
        if filename == '-':
            filename = '<STDIN>'
        self.filename = filename
        single_quotes = '(found single quotes not double quotes)'
        self.valid_json_msg_single_quotes = '{0} {1}'.format(self.valid_json_msg, single_quotes)
        self.invalid_json_msg_single_quotes = '{0} {1}'.format(self.invalid_json_msg, single_quotes)
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
            self.check_file(filename)
        if self.failed:
            sys.exit(2)

    def check_file(self, filename):
        if self.is_excluded(filename):
            return
        mem_err = "file '%s', assuming Big Data multi-record json and re-trying validation line-by-line" % filename
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


if __name__ == '__main__':
    JsonValidatorTool().main()
