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
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

CSV Validator Tool

Validates each file passed as an argument

Directories are recursed, checking all files ending in a .csv suffix.

Works like a standard unix filter program - if no files are passed as arguments or '-' is given then reads
from standard input

This is not as good as the other validate_*.py programs in this repo as the others have clearer syntactic structure
to check. CSV/TSV has higher variation with delimiters, quote characters etc. If delimiters and quotechars are not
specified it'll try to infer the structure but I've had to add a few heuristics to invalidate files which otherwise
pass python csv module's inference including json and yaml files which we don't accept.

Explicitly using the --delimiter option will disable the inference which is handy if it's
allowing through non-csv files, you don't want to accept other delimited files such as TSV files etc.

This may be fine for simple purposes but for a better validation tool with more options see:

https://pythonhosted.org/chkcsv/

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# this causes csvreader TypeError: the "delimiter" must be an 1-character string
# from __future__ import unicode_literals

import csv
import os
import re
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, log_option, uniq_list_ordered, log, isChars, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.10.0'


class CsvValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(CsvValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.filename = None
        # self.delimiter = ','
        # self.quotechar = '"'
        # allow CSV module inference - this way user can choose to explicitly specify --delimiter=, --quotechar='"'
        # or allow to try to infer itself
        self.delimiter = None
        self.quotechar = None
        self.re_csv_suffix = re.compile(r'.*\.csv$', re.I)
        self.valid_csv_msg = '<unknown> => CSV OK'
        self.invalid_csv_msg = '<unknown> => CSV INVALID'
        self.failed = False
        self.exclude = None

    def add_options(self):
        # do not leave as None to infer per line, it'll split a single word line like 'blah' => ['b', 'ah']
        # and there is no way to detect it only had one field
        self.add_opt('-d', '--delimiter', default=',',
                     help='Delimiter to test (default: comma)')
        self.add_opt('-q', '--quotechar', default=self.quotechar,
                     help='Quotechar to test (default: None)')
    #   self.add_opt('-p', '--print', action='store_true',
    #                help='Print the CSV lines(s) which are valid, else print nothing (useful for shell ' +
    #                'pipelines). Exit codes are still 0 for success, or %s for failure'
    #                % ERRORS['CRITICAL'])
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

    def process_csv(self, filehandle):
        csvreader = None
        try:
            if self.delimiter is not None:
                try:
                    csvreader = csv.reader(filehandle, delimiter=self.delimiter, quotechar=self.quotechar)
                except TypeError as _:
                    self.usage(_)
            else:
                # dialect = csv.excel
                dialect = csv.Sniffer().sniff(filehandle.read(1024))
                # this will raise an Error if invalid
                dialect.strict = True
                filehandle.seek(0)
                csvreader = csv.reader(filehandle, dialect)
        except csv.Error  as _:
            log.warning('file %s: %s', self.filename, _)
            return False
        count = 0
        try:
            # csvreader doesn't seem to generate any errors ever :-(
            # csv module allows entire lines of json/xml/yaml to go in as a single field
            # Adding some invalidations manually
            for field_list in csvreader:
                # list of fields with no separator information
                # log.debug("line: %s", _)
                # make it fail if there is only a single field on any line
                if len(field_list) < 2:
                    return False
                # it's letting JSON through :-/
                if field_list[0] == '{':
                    return False
                # extra protection along the same lines as anti-json:
                # the first char of field should be alphanumeric, not syntax
                # however instead of isAlnum allow quotes for quoted CSVs to pass validation
                if not isChars(field_list[0][0], 'A-Za-z0-9\'"'):
                    return False
                count += 1
        except csv.Error  as _:
            log.warning('file %s, line %s: %s', self.filename, csvreader.line_num, _)
            return False
        if count == 0:
            log.debug('zero lines detected, blank input is not valid CSV')
            return False
        log.debug('%s CSV lines passed', count)
        return True

    def check_csv(self, filehandle):
        if self.process_csv(filehandle):
            # if self.get_opt('print'):
            #     print(content, end='')
            # else:
            #     print(self.valid_csv_msg)
            print(self.valid_csv_msg)
        else:
            self.failed = True
            # if not self.get_opt('print'):
            #     if self.verbose > 2:
            #         try:
            #         except csv.Error as _:
                        # if not self.get_opt('print'):
                        #     print(_)
                # die(self.invalid_csv_msg)
            die(self.invalid_csv_msg)

    def run(self):
        self.delimiter = self.get_opt('delimiter')
        self.quotechar = self.get_opt('quotechar')
        log_option('delimiter', self.delimiter)
        log_option('quotechar', self.quotechar)
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
                die("path '{0}' could not be determined as either a file or directory".format(arg))
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
                if self.re_csv_suffix.match(file_path):
                    self.check_file(file_path)

    def check_file(self, filename):
        self.filename = filename
        if self.filename == '-':
            self.filename = '<STDIN>'
        self.valid_csv_msg = '%s => CSV OK' % self.filename
        self.invalid_csv_msg = '%s => CSV INVALID' % self.filename
        if self.filename == '<STDIN>':
            log.debug('checking stdin')
            self.check_csv(sys.stdin)
        else:
            if self.is_excluded(filename):
                return
            log.debug('checking %s', self.filename)
            try:
                with open(self.filename) as iostream:
                    self.check_csv(iostream)
            except IOError as _:
                die("ERROR: %s" % _)


if __name__ == '__main__':
    CsvValidatorTool().main()

# =========================================================================== #
# borrowed and tweaked from Python standard library:
# https://docs.python.org/2/library/csv.html

# import codecs
# import cStringIO

# class UTF8Recoder(object):
#     """
#     Iterator that reads an encoded stream and reencodes the input to UTF-8
#     """
#     def __init__(self, _, encoding):
#         self.reader = codecs.getreader(encoding)(_)
#
#     def __iter__(self):
#         return self
#
#     def next(self):
#         return self.reader.next().encode("utf-8")
#
#
# class UnicodeReader(object):
#     """
#     A CSV reader which will iterate over lines in the CSV filehandle,
#     which is encoded in the given encoding.
#     """
#
#     def __init__(self, _, dialect=csv.excel, encoding="utf-8", **kwargs):
#         _ = UTF8Recoder(_, encoding)
#         self.reader = csv.reader(_, dialect=dialect, **kwargs)
#
#     def next(self):
#         row = self.reader.next()
#         return [unicode(s, "utf-8") for s in row]
#
#     def __iter__(self):
#         return self
