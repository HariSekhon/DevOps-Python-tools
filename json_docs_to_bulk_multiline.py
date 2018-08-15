#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-07-28 17:08:47 +0200 (Fri, 28 Jul 2017)
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

Tool to convert JSON document per file to one document per line for bulk JSON data handling
in Big Data systems like Hadoop (MongoDB can also use this multi-doc format)

Directories if given are detected and recursed, checking all files in the directory tree ending in a .json suffix.

First tries each file contents as a whole json document, if that fails validation or catches a memory error, then
it assumes the file contains Big Data / MongoDB data with one json document per line and tries to validate each
line as a json document, which means you can conveniently convert a mix of both formats in to one unified bulk output.

Works like a standard unix filter program - if no files are passed as arguments or '-' is passed then reads from
standard input in which case it expects a single document as mixing docs and multi-line bulk in same standard input
stream would make no sense and piping just bulk multi-line wouldn't need converting anyway.

Output is written to standard output as per standard unix tools so that the output stream can be easily redirected
or further manipulated easily in shell pipelines, eg. piped in to HDFS or undergo further string manipulation tools

Broken json documents are printed to standard error for collecting to an error log

Single quoted JSON while not technically valid is supported as some systems like MongoDB permit it, and it has handling
which permits detecting and escaping embedded double quotes if necessary, as well as skipping blank lines in
multi-record json for convenience

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# from __future__ import unicode_literals

import json
import os
import re
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import isJson, die, printerr, ERRORS, log_option, uniq_list_ordered, validate_regex
    from harisekhon.utils import log
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.0'

# TODO: unify all validate_* and this programs in to a class hierarchy as a lot of the code is similar


class JsonDocsToBulkMultiline(CLI):

    def __init__(self):
        # Python 2.x
        super(JsonDocsToBulkMultiline, self).__init__()
        # Python 3.x
        # super().__init__()
        self.iostream = None
        self.re_json_suffix = re.compile(r'.*\.json$', re.I)
        self.permit_single_quotes = False
        self.failed = False
        self.continue_on_error = False
        self.single_quotes_detected = False
        self.exclude = None

    def add_options(self):
        self.add_opt('-s', '--permit-single-quotes', dest='permit_single_quotes', action='store_true', default=False,
                     help='Accept single quotes as valid (JSON standard requires double quotes but some' +
                     ' systems like MongoDB are ok with single quotes)')
        self.add_opt('-c', '--continue-on-error', action='store_true', default=False,
                     help='Continue on errors, do not exit early, will still omit a warning error code of 1 ' + \
                          'at the end instead of dying with critical error code 2 immediately, either way '   + \
                          'broken documents are printed to standard error for collection redirect to an error log')
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

    def run(self):
        self.permit_single_quotes = self.get_opt('permit_single_quotes')
        self.continue_on_error = self.get_opt('continue_on_error')
        log_option('permit single quotes', self.permit_single_quotes)
        log_option('continue on error', self.continue_on_error)
        if not self.args:
            self.args.append('-')
        args = uniq_list_ordered(self.args)
        # this will given a list of inputs at the start of the program
        for arg in args:
            log_option('path', arg)
            if arg == '-':
                continue
            if not os.path.exists(arg):
                print("'{0}' not found".format(arg))
                sys.exit(ERRORS['CRITICAL'])
        for arg in args:
            self.process_path(arg)
        if self.failed:
            sys.exit(ERRORS['CRITICAL'])

    @staticmethod
    def convert_single_quoted(content):
        return content.replace("'", '"')

    def convert_single_quoted_escaped(self, content):
        return self.convert_single_quoted(content.replace('"', r'\"'))

    def process_multirecord_json(self, filename):
        log.debug('process_multirecord_json()')
        log.debug('rewinding I/O stream')
        self.iostream.seek(0)
        for line in self.iostream:
            if line.strip() == '':
                continue
            if self.process_json(line, filename):
                continue
        if self.failed:
            return False
        return True

    def process_json(self, content, filename):
        log.debug('process_json()')
        if not content:
            log.warning("blank content passed to process_json for contents of file '%s'", filename)
        if isJson(content):
            print(json.dumps(json.loads(content)))
            return True
        elif self.permit_single_quotes:
            log.debug('checking for single quoted JSON')
            # check if it's regular single quoted JSON a la MongoDB
            json_single_quoted = self.convert_single_quoted(content)
            if self.process_json_single_quoted(json_single_quoted, filename):
                return True
            log.debug('single quoted JSON check failed, trying with pre-escaping double quotes')
            # check if it's single quoted JSON with double quotes that aren't escaped,
            # by pre-escaping them before converting single quotes to doubles for processing
            json_single_quoted_escaped = self.convert_single_quoted_escaped(content)
            if self.process_json_single_quoted(json_single_quoted_escaped, filename):
                log.debug("processed single quoted json with non-escaped double quotes in '%s'", filename)
                return True
            log.debug('single quoted JSON check failed even with pre-escaping any double quotes')
        self.failed = True
        log.error("invalid json detected in '%s':", filename)
        printerr(content)
        if not self.continue_on_error:
            sys.exit(ERRORS['CRITICAL'])
        return False

    def process_json_single_quoted(self, content, filename):
        if isJson(content):
            if not self.single_quotes_detected:
                log.debug("detected single quoted json in '%s'", filename)
                self.single_quotes_detected = True
            print(json.dumps(json.loads(content)))
            return True
        return False

    # looks like this does a .read() anyway, not buying any efficiency enhancement
    #
    #  usage:
    # self.process_json_fp(self.iostream)
    # must reset afterwards, otherwise next check will result in Invalid JSON due to blank
    # self.iostream.seek(0)
    #
    # def process_json_fp(self, fp):
    #     try:
    #         json.load(fp)
    #         return True
    #     except ValueError:
    #         die(self.invalid_json_msg)

    def process_path(self, path):
        if self.is_excluded(path):
            return
        if path == '-' or os.path.isfile(path):
            self.process_file(path)
        elif os.path.isdir(path):
            self.walk(path)
        else:
            die("path '{0}' could not be determined as either a file or directory".format(path))

    # don't need to recurse when using this - so only process os.path.join(root, filename)
    def walk(self, path):
        for root, dirs, files in os.walk(path, topdown=True):
            # modify dirs in place to prune descent for increased efficiency
            # requires topdown=True
            # calling is_excluded() on joined root/dir so that things like
            #   '/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+' will match
            dirs[:] = [d for d in dirs if not self.is_excluded(os.path.join(root, d))]
            for filename in files:
                file_path = os.path.join(root, filename)
                if self.re_json_suffix.match(file_path):
                    self.process_file(file_path)

    def process_file(self, filename):
        if self.is_excluded(filename):
            return
        if filename == '-':
            self.iostream = sys.stdin
            self.process_json(sys.stdin.read(), '<STDIN>')
        else:
            # reset this flag which we use to only print single quote detection once per file
            self.single_quotes_detected = False
            try:
                with open(filename) as self.iostream:
                    # check if it's a Big Data format file with json doc on first line
                    # this is more efficient than slurping a large file only to fail with out of memory
                    for _ in range(1, 10):
                        line = self.iostream.readline()
                        if line:
                            if isJson(line) or \
                               isJson(self.convert_single_quoted(line)) or \
                               isJson(self.convert_single_quoted_escaped(line)):
                                log.debug("header line of '{0}' detected as a valid JSON document".format(filename) +
                                          ", assuming Big Data format multi-line json")
                                self.process_multirecord_json(filename)
                                break
                    else:
                        try:
                            self.iostream.seek(0)
                            content = self.iostream.read()
                            self.process_json(content, filename)
                        except MemoryError:
                            # may be a big data format after all and perhaps the first record was broken
                            log.warning("memory error validating contents from file '{0}', ".format(filename) +
                                        "assuming Big Data multi-record json and re-trying validation line-by-line")
                            self.process_multirecord_json(filename)
            except IOError as _:
                die("ERROR: %s" % _)


if __name__ == '__main__':
    JsonDocsToBulkMultiline().main()
