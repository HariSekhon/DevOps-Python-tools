#!/usr/bin/env python
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-07-31 11:03:17 +0100 (Fri, 31 Jul 2020)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Finds missing files by numeric sequence, assuming a uniformly numbered file naming convention across files

Files / directories are given as arguments or via standard input

Directories are recursed

You must only give directories that should be sharing a contiguously numbered file naming convention for each
single run of this tool

Accounts for zero padding in numbered files

Caveats:

- This is more complicated than you'd first think as there are so many file naming variations so this is not the most
  universally bulletproof piece of code in this repo by a long shot and may require advanced tuning --regex tuning to
  match your use case

- Won't detect missing files higher than the highest numbered file as there is no way to know how many there should be.
  If you are looking for missing MP3 files, then you might be able to use 'mediainfo' to get the max track position and
  see if the files go that high

- Returns globs instead of explicit missing filenames since suffixes can vary after numbers. If you have a simple enough
  use case with a single fixed filename convention such as 'blah_01.txt' then you can find code to print the missing
  files more explicitly, but in the general case you cannot account for suffix naming that isn't consistent, such as
  chapters of audiobooks eg.

        'blah 01 - chapter 1.mp3'
        'blah 02 - chapter 2.mp3'

  so in the general case you cannot always infer suffixes, hence why it is left as globs.
  Simpler single use case scripts would be better for printing explicit missing files as they can use hardcoded suffixes

- Doesn't currently find entire missing CD / disks in the naming format, but you should be able to see those cases
  easily by eye

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import glob
#import logging
import os
import re
import sys
import traceback
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    from harisekhon.utils import log, log_option, validate_regex, isFloat, UnknownError
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'


class FindMissingFiles(CLI):

    def __init__(self):
        # Python 2.x
        super(FindMissingFiles, self).__init__()
        # Python 3.x
        # super().__init__()
        self.paths = []
        self.regex_default = r'(?<!dis[ck]\s)(?<!CD\s)(?<!0)(\d+(?:\.\d+)?)'
        self.regex = None
        self.include = None
        self.exclude = None

    def add_options(self):
        super(FindMissingFiles, self).add_options()
        self.add_opt('-r', '--regex', metavar='REGEX', default=self.regex_default,
                     help='Regex capture of the portion of the filename to compare ' + \
                          '(default: "{}" -  must have capture brackets capturing an integer or float)'\
                          .format(self.regex_default))
        self.add_opt('-i', '--include', metavar='REGEX',
                     help='Include only files that match the given case-insensitive regex (eg. ".mp3$")')
        self.add_opt('-e', '--exclude', metavar='REGEX',
                     help='Exclude files that match the given case-insensitive regex (eg. ".mp3$")')

    def process_options(self):
        super(FindMissingFiles, self).process_options()
        self.regex = self.get_opt('regex')
        self.include = self.get_opt('include')
        self.exclude = self.get_opt('exclude')
        validate_regex(self.regex)
        # file names are often not exactly 'blah 01.mp3' and may instead be:
        # 'blah 01 - chapter 1.mp3'
        # 'blah 02 - chapter 2.mp3'
        # - so you cannot infer suffixes
        #self.regex = re.compile('(.*?)' + self.regex + '(.*)', re.I)
        self.regex = re.compile('(.*?)' + self.regex, re.I)
        if self.include is not None:
            validate_regex(self.include)
            self.include = re.compile(self.include, re.I)
        if self.exclude is not None:
            validate_regex(self.exclude)
            self.exclude = re.compile(self.exclude, re.I)
        if len(self.args) > 0:
            self.paths = self.args
        else:
            self.paths = sys.stdin.readlines()
        log_option('paths', self.paths)

    def is_included(self, path):
        if not self.include:
            return True
        if self.include.search(path):
            log.debug("including path: %s", path)
            return True
        return False

    def is_excluded(self, path):
        if not self.exclude:
            return False
        if self.exclude.search(path):
            log.debug("excluding path: %s", path)
            return True
        return False

    def run(self):
        for path in self.paths:
            if self.is_excluded(path):
                continue
            if not self.is_included(path):
                continue
            if not os.path.exists(path):
                raise UnknownError('path not found: {}'.format(path))
            if os.path.isdir(path):
                self.process_directory(directory=path)
            elif os.path.isfile(path):
                self.check_file(filename=path)

    def process_directory(self, directory):
        for root, dirs, files in os.walk(directory, topdown=True):
            for filename in files:
                file_path = os.path.join(root, filename)
                if not self.is_included(file_path):
                    continue
                if self.is_excluded(file_path):
                    continue
                self.check_file(filename=file_path)
            for dirname in dirs:
                dir_path = os.path.join(root, dirname)
                if not self.is_included(dir_path):
                    continue
                if self.is_excluded(dir_path):
                    continue
                self.process_directory(directory=dir_path)

    def check_file(self, filename):
        log.debug('checking file \'%s\'', filename)
        match = self.regex.search(filename)
        if not match:
            log.debug('failed to match file \'%s\', skipping...', filename)
            return
        # will error out here if you've supplied your own regex without capture brackets
        # or if you've got pre-captures - let this bubble to user to fix their regex
        file_prefix = match.group(1)
        file_number = match.group(2)
        if not isFloat(file_number):
            raise UnknownError('regex captured non-float for filename: {}'.format(filename))
        if file_prefix is None:
            file_prefix = ''
        padding = len(file_number)
        file_number = int(file_number)
        self.determine_missing_file_backfill(file_prefix, file_number, padding)

    def determine_missing_file_backfill(self, file_prefix, file_number, padding):
        if file_number != 1:
            file_number -= 1
            expected_last_filename_glob = '{}{:0>%(padding)s}*' % locals()
            expected_last_filename_glob = expected_last_filename_glob.format(file_prefix, file_number)
            if not glob.glob(expected_last_filename_glob):
                # by recursing and printing on the unwind we get correctly ordered file numbering ascending
                self.determine_missing_file_backfill(file_prefix, file_number, padding)
                print(expected_last_filename_glob)


if __name__ == '__main__':
    FindMissingFiles().main()
