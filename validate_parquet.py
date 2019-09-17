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

Parquet Validator Tool

Validates each file passed as an argument

Directories are recursed, checking all files ending in a .parquet suffix.

Works like a standard unix filter program - if no files are passed as arguments or '-' is given then reads
from standard input.

There is no good comprehensive Python Parquet module so it must use parquet-cat from parquet-tools.

Parquet-tools must be either in the $PATH or adjacent to this program (it's downloaded as part of the automated
'make' build). Things like passing data through stdin requires writing out to a tempfile (which is auto-cleaned up
afterwards) and then reading it back in parquet tools, which is non-ideal in terms of performance.

"""

# This module doesn't have full parquet support and will therefore break on some parquet files
# https://github.com/jcrobak/parquet-python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# from __future__ import unicode_literals

import glob
import os
import re
import subprocess
import sys
import tempfile
#try:
#    import pyarrow.parquet as pq
#except ImportError as _:
#    print('module import failed: %s' % _, file=sys.stderr)
#    sys.exit(4)
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, log_option, log, which, uniq_list_ordered, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.9.1'


class ParquetValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(ParquetValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.timeout_default = 60
        self.re_parquet_suffix = re.compile(r'.*\.parquet$', re.I)
        self.valid_parquet_msg = '<unknown> => Parquet OK'
        self.invalid_parquet_msg = '<unknown> => Parquet INVALID'
        self.exclude = None
        for _ in reversed(glob.glob(os.path.join(os.path.dirname(__file__), 'parquet-tools-*'))):
            if os.path.isdir(_):
                log.debug('adding %s to $PATH' % _)
                os.environ['PATH'] += ':' + os.path.abspath(_)

    def add_options(self):
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

    def check_parquet(self, filename):
        stderr = subprocess.PIPE
        if self.verbose > 2:
            stderr = None
        if not which('parquet-cat'):
            die('parquet-cat not found in $PATH')
        if subprocess.call(['parquet-cat', filename], stdout=subprocess.PIPE, stderr=stderr, shell=False) == 0:
        # not very tolerant, get exception with this error:
        # pyarrow.lib.ArrowNotImplementedError: No support for reading columns of type list<array: int32 not null>
        #if pq.read_table(filename):
            print(self.valid_parquet_msg)
        else:
            die(self.invalid_parquet_msg)

    def run(self):
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

    def check_path(self, path):
        if path == '-' or os.path.isfile(path):
            self.check_file(path)
        elif os.path.isdir(path):
            self.walk(path)
        else:
            die("failed to determine if path '%s' is file or directory" % path)

#    def walk(self, path):
#        for item in os.listdir(path):
#            subpath = os.path.join(path, item)
#            if os.path.isdir(subpath):
#                self.check_path(subpath)
#            elif self.re_parquet_suffix.match(item):
#                self.check_file(subpath)

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
                if self.re_parquet_suffix.match(file_path):
                    self.check_file(file_path)

    def check_file(self, filename):
        if filename == '-':
            filename = '<STDIN>'
        self.valid_parquet_msg = '%s => Parquet OK' % filename
        self.invalid_parquet_msg = '%s => Parquet INVALID' % filename
        if filename == '<STDIN>':
            try:
                tmp = tempfile.NamedTemporaryFile()
                log.debug('created tmp file from stdin: %s', tmp.name)
                tmp.write(sys.stdin.read())
                tmp.seek(0)
                self.check_parquet(tmp.name)
                tmp.close()
            except IOError as _:
                die("ERROR: %s" % _)
        else:
            if self.is_excluded(filename):
                return
            try:
                self.check_parquet(filename)
            except IOError as _:
                die("ERROR: %s" % _)


if __name__ == '__main__':
    ParquetValidatorTool().main()
