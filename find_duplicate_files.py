#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-08-14 09:50:03 +0100 (Sun, 14 Aug 2016)
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

Tool to find duplicate files in given directory trees

Compares files by multiple approaches:

By default will compare files via both of the following methods:

1. basename
2. size + MD5 checksum - for efficiency only files with identical byte counts are MD5'd to see if they're really the
                         same file. Zero byte files are ignored for this test as they're not real duplicates and
                         obscure the real results (instead you can find them easily via 'find . -type f -size 0')

Additional methods available:

3. size only - if explicitly requested only, otherwise will backtrack to checksum the original to be more accurate
4. regex capture matching portion - specify a regex to match against the filenames with capture (brackets) and the
                                    captured portion will be compared among files. If no capture brackets are detected
                                    then will treat the entire regex as the capture.
                                    Regex is case insensitive by default and applies only to the file's basename

Exits with exit code 4 if duplicates are found

Can restrict methods of finding duplicates to any combination of --name / --size / --checksum (checksum implies size as
an efficiency shortcut) / --regex. If none are specified then will try name, size + checksum. If specifying any one of
these options then the others will not run unless also explicitly specified.

If you want to find files that are probably the same by byte count but may not have the same checksum due to minor
corruption, such as large media files, then specify --size but do not specify --checksum which supercedes it

Caveats:

- The limitation of the checksum approach is that it can't determine files as duplicates if there is any
slight imperfection in one of the files (eg. multimedia files) as that would result in differing checksums.

- By default this program will short-circuit to stop processing a file as soon as it is determined to be a duplicate
file via one of the above methods in that order for efficiency. This means that if 2 files have duplicate names,
and a third has a different name but the same checksum as the second one, the second one's size + checksum will not have
been checked and so a third duplicate with a different name will not be detected by size / checksum. In most cases this
is a good thing to finish quicker and avoid unnecessary checksumming which is computationally expensive and time
consuming for large files. If you remove one duplicate then the next run of this program would find the other
duplicate via the additional checks of size and checksumming. Given it's a rare condition it's probably not worth the
extra overhead in everyday use but this behaviour can be overridden by specifying the --no-short-circuit option to run
every check on every file. Be aware this will slow down the process.

To see progress of which files are matching size, backtracking to hash them for comparison etc
use --verbose twice or -vv. To see which files are being checked use triple verbose mode -vvv

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import hashlib
import itertools
import logging
import os
import re
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, log, log_option, uniq_list_ordered, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6.2'


class FindDuplicateFiles(CLI):

    def __init__(self):
        # Python 2.x
        super(FindDuplicateFiles, self).__init__()
        # Python 3.x
        # super().__init__()
        self.failed = False
        self.quiet = False
        self.timeout_default = 86400
        self.regex = None
        self.re_compiled = None
        self.files = {}
        self.sizes = {}
        self.hashes = {}
        self.regex_captures = {}
        self.no_short_circuit = False
        self.include_dot_dirs = False
        # Basenames for files, dot dirs are ignored by default unless using --include-dot-dirs
        self.ignore_list = [
            '.DS_Store'
            ]
        self.ignore_list = [_.lower() for _ in self.ignore_list]
        self.dups_by_name = {}
        self.dups_by_size = {}
        self.dups_by_hash = {}
        self.dups_by_regex = {}
        self.dup_filepaths = set()
        self.compare_by_name = False
        self.compare_by_size = False
        self.compare_by_checksum = False

    def add_options(self):
        self.add_opt('-n', '--name', help='Find duplicates by file basename', action='store_true', default=False)
        self.add_opt('-s', '--size', help='Find duplicates by file size', action='store_true', default=False)
        self.add_opt('-c', '--checksum', action='store_true', default=False,
                     help='Find duplicates by file size + checksum')
        self.add_opt('-r', '--regex', help='Find duplicates by regex partial name match. Advanced Feature, regex '
                     + 'must contain capture brackets, only first capture brackets will be '
                     + 'used and their matching contents compared across files')
        self.add_opt('-o', '--no-short-circuit', action='store_true', default=False,
                     help='Do not short-circuit finding duplicates, see --help description')
        self.add_opt('-d', '--include-dot-dirs', action='store_true', default=False,
                     help='Included hidden .dot directories (excluded by default to avoid .git which has lots '
                     + 'of small files)')
        self.add_opt('-q', '--quiet', action='store_true', default=False,
                     help='Only output file paths with duplicates (for use in shell scripts)')

    # @override, must use instance method, not static method, in order to match
    def setup(self):  # pylint: disable=no-self-use
        log.setLevel(logging.ERROR)

    #def print(self, *args, **kwargs):
    #    if not self.quiet:
    #        print(*args, **kwargs)

    def process_args(self):
        args = uniq_list_ordered(self.args)
        if not args:
            self.usage('no directories specified as arguments')
        log_option('directories', args)
        self.compare_by_name = self.get_opt('name')
        self.compare_by_size = self.get_opt('size')
        self.compare_by_checksum = self.get_opt('checksum')
        self.regex = self.get_opt('regex')
        self.quiet = self.get_opt('quiet')
        self.no_short_circuit = self.get_opt('no_short_circuit')
        self.include_dot_dirs = self.get_opt('include_dot_dirs')
        if self.regex:
            if '(' not in self.regex:
                log.info('regex no capture brackets specified, will capture entire given regex')
                self.regex = '(' + self.regex + ')'
            validate_regex(self.regex)
            self.re_compiled = re.compile(self.regex, re.I)
        if not (self.compare_by_name or self.compare_by_size or self.compare_by_checksum or self.regex):
            self.compare_by_name = True
            #self.compare_by_size = True
            self.compare_by_checksum = True
        log_option('compare by name', self.compare_by_name)
        log_option('compare by size', self.compare_by_size)
        log_option('compare by checksum', self.compare_by_checksum)
        log_option('compare by regex', bool(self.regex))
        return args

    @staticmethod
    def check_args(args):
        for arg in args:
            if not os.path.exists(arg):
                _ = "'%s' not found" % arg
                #if self.skip_errors:
                #    log.error(_)
                #    self.failed = True
                #else:
                die(_)
            if os.path.isfile(arg):
                log_option('file', arg)
            elif os.path.isdir(arg):
                log_option('directory', arg)
            else:
                die("path '%s' could not be determined as either a file or directory" % arg)

    def run(self):
        args = self.process_args()
        self.check_args(args)
        for arg in args:
            try:
                self.check_path(arg)
            except OSError as _:
                log.error(_)
                self.failed = True
        if self.dups_by_name or \
           self.dups_by_size or \
           self.dups_by_hash or \
           self.dups_by_regex:
            if self.quiet:
                for _ in self.dups_by_name:
                    self.dup_filepaths.add(_)
                for _ in itertools.chain.from_iterable(self.dups_by_size.itervalues()):
                    self.dup_filepaths.add(_)
                for _ in itertools.chain.from_iterable(self.dups_by_hash.itervalues()):
                    self.dup_filepaths.add(_)
                for _ in itertools.chain.from_iterable(self.dups_by_regex.itervalues()):
                    self.dup_filepaths.add(_)
                for filepath in sorted(self.dup_filepaths):
                    print(filepath)
                sys.exit(4)
            print('# Duplicates detected!')
            if self.dups_by_name:
                print('\n# Duplicates by name:\n')
                for basename in self.dups_by_name:
                    print("# --\n# basename '{0}':".format(basename))
                    for filepath in sorted(self.dups_by_name[basename]):
                        print(filepath)
            if self.dups_by_size:
                print('\n# Duplicates by size:\n')
                for size in self.dups_by_size:
                    print("# --\n# size '{0}' bytes:".format(size))
                    for filepath in sorted(self.dups_by_size[size]):
                        print(filepath)
            if self.dups_by_hash:
                print('\n# Duplicates by checksum:\n')
                for checksum in self.dups_by_hash:
                    print("# --\n# checksum '{0}':".format(checksum))
                    for filepath in sorted(self.dups_by_hash[checksum]):
                        print(filepath)
            if self.dups_by_regex:
                print('\n# Duplicates by regex match ({0}):\n'.format(self.regex))
                for matching_portion in self.dups_by_regex:
                    print("# --\n# regex matching portion '{0}':".format(matching_portion))
                    for filepath in sorted(self.dups_by_regex[matching_portion]):
                        print(filepath)
            sys.exit(4)
        elif self.failed:
            sys.exit(2)
        else:
            print('# No Duplicates Found')
            sys.exit(0)

#    def check_path(self, path):
#        if os.path.isfile(path):
#            self.check_file(path)
#        elif os.path.isdir(path):
#            listing = []
#            try:
#                listing = os.listdir(path)
#                listing = [x for x in listing if x[0] != '.']
#            except OSError as _:
#                print(_)
#                self.failed = True
#            for item in listing:
#                subpath = os.path.join(path, item)
#                if os.path.isdir(subpath):
#                    self.check_path(subpath)
#                else:
#                    try:
#                        self.is_file_dup(subpath)
#                    except OSError as _:
#                        log.error("error while checking file '{0}': {1}".format(subpath, _))
#                        self.failed = True
#        else:
#            die("failed to determine if path '%s' is file or directory" % path)

    def check_path(self, path):
        # os.walk returns nothing if path is a file, and must store file names, sizes, checksums and regex captures
        # even for standalone file args
        if os.path.isfile(path):
            self.is_file_dup(path)
        elif os.path.isdir(path):
            # returns generator
            # root is the dir, dirs and files are child basenames
            #for root, dirs, files in os.walk(path):
            for root, dirs, files in os.walk(path):
                #log.debug('root = %s', root)
                #log.debug('files = %s', files)
                # do not check hidden subdirs
                if not self.include_dot_dirs:
                    # results in 'IndexError: string index out of range' if suffixed with '/'
                    # if os.path.basename(root)[0] == '.':
                    #    continue
                    # could regex strip all suffixed '/' but it's cheaper to just modify the dirs list in place
                    dirs[:] = [d for d in dirs if d[0] != '.']
                for filebasename in files:
                    filepath = os.path.join(root, filebasename)
                    try:
                        self.is_file_dup(filepath)
                    except OSError as exc:
                        log.error("error while checking file '{0}': {1}".format(filepath, exc))
                        self.failed = True
        else:
            die("'%s' is not a file or directory")

    def is_file_dup(self, filepath):
        log.debug("checking file path '%s'", filepath)
        # pylint: disable=no-else-return
        if os.path.islink(filepath):
            log.debug("ignoring symlink '%s'", filepath)
            return False
        elif os.path.basename(filepath).lower() in self.ignore_list:
            log.debug("ignoring file '%s', basename '%s' is in ignore list", filepath, os.path.basename(filepath))
            return False
        is_dup = False
        if self.compare_by_name:
            if self.is_file_dup_by_name(filepath):
                if not self.no_short_circuit:
                    return True
                else:
                    is_dup = True
        if self.compare_by_checksum:
            if self.is_file_dup_by_hash(filepath):
                if not self.no_short_circuit:
                    return True
                else:
                    is_dup = True
        elif self.compare_by_size:
            if self.is_file_dup_by_size(filepath):
                if not self.no_short_circuit:
                    return True
                else:
                    is_dup = True
        if self.regex:
            if self.is_file_dup_by_regex(filepath):
                if not self.no_short_circuit:
                    return True
                else:
                    is_dup = True
        if is_dup:
            return True
        return False

    def is_file_dup_by_name(self, filepath):
        basename = os.path.basename(filepath)
        #log.debug("checking file path '%s' basename '%s'", filepath, basename)
        if basename in self.files:
            self.dups_by_name[basename] = self.dups_by_name.get(basename, set())
            self.dups_by_name[basename].add(self.files[basename])
            self.dups_by_name[basename].add(filepath)
            return True
        self.files[basename] = filepath
        return False

    def is_file_dup_by_size(self, filepath):
        size = os.stat(filepath).st_size
        log.debug("file '%s' size '%s'", filepath, size)
        if size == 0:
            log.warn("skipping zero byte file '%s'", filepath)
            return 0
        if size in self.sizes:
            if self.compare_by_size:
                self.dups_by_size[size] = self.dups_by_size.get(size, set())
                self.dups_by_size[size].add(*self.sizes[size])
                self.dups_by_size[size].add(filepath)
            return size
        self.sizes[size] = self.sizes.get(size, {})
        self.sizes[size][filepath] = None
        return False

    @staticmethod
    def hash(filepath):
        with open(filepath) as _:
            return hashlib.md5(_.read()).hexdigest()

    def is_file_dup_by_hash(self, filepath):
        checksum = None
        size = self.is_file_dup_by_size(filepath)
        if size:
            log.info("found file '%s' of matching size '%s' bytes", filepath, size)
            checksum = self.hash(filepath)
            self.sizes[size][filepath] = checksum
            self.hashes[checksum] = self.hashes.get(checksum, set())
            self.hashes[checksum].add(filepath)
        else:
            self.sizes[size] = {}
            self.sizes[size][filepath] = None

        sizeitem = self.sizes[size]
        if len(sizeitem) < 2:
            pass
        elif len(sizeitem) == 2:
            for filepath in sizeitem:
                if sizeitem[filepath] is None:
                    log.info("backtracking to now hash first file '%s'", filepath)
                    checksum = self.hash(filepath)
                    sizeitem[filepath] = checksum
                    self.hashes[checksum] = self.hashes.get(checksum, set())
                    self.hashes[checksum].add(filepath)
        if checksum is not None and len(self.hashes[checksum]) > 1:
            self.dups_by_hash[checksum] = self.dups_by_hash.get(checksum, set())
            for filepath2 in self.hashes[checksum]:
                self.dups_by_hash[checksum].add(filepath2)
            return True
        return False

    def is_file_dup_by_regex(self, filepath):
        #match = re.search(self.regex, filepath)
        basename = os.path.basename(filepath)
        match = re.search(self.regex, basename)
        if match:
            log.debug("regex matched file '%s'", filepath)
            if match.groups():
                capture = match.group(1)
            else:
                capture = match.group(0)
            if capture in self.regex_captures:
                self.dups_by_regex[capture] = self.dups_by_regex.get(capture, set())
                self.dups_by_regex[capture].add(self.regex_captures[capture])
                self.dups_by_regex[capture].add(filepath)
                return True
            self.regex_captures[capture] = filepath
        return False


if __name__ == '__main__':
    FindDuplicateFiles().main()
