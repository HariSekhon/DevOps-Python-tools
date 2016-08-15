#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-08-14 09:50:03 +0100 (Sun, 14 Aug 2016)
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

Tool to find duplicate files in given directory trees

Compares files by 2 approaches:

1. basename
2. size and MD5 checksum - for efficiency only files with identical byte counts are MD5'd to see if they're really the
                           same file. Zero byte files are ignored for this test as they're not real duplicates and
                           obscure the real results (instead you can find them easily via 'find . -type f -size 0')

The limitation of this approach is that it won't find files as duplicates if there is a slight imperfection in one of
the files as that would result in a differing MD5.

"""

# XXX: One thing I'd like to add to this would be generic name mangling rules but this is tricky to do, perhaps could
#      be added via regex with captures

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import hashlib
import os
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, log, log_option, uniq_list_ordered
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2'

class FindDuplicateFiles(CLI):

    def __init__(self):
        # Python 2.x
        super(FindDuplicateFiles, self).__init__()
        # Python 3.x
        # super().__init__()
        self.failed = False
        self.timeout_default = 86400
        self.files = {}
        self.sizes = {}
        self.hashes = {}
        self.dups_by_name = {}
        self.dups_by_hash = {}

    def process_args(self):
        args = uniq_list_ordered(self.args)
        if not args:
            self.usage('no directories specified as arguments')
        log_option('directories', args)
        return args

    def check_args(self, args):
        for arg in args:
            if not os.path.exists(arg):
                _ = "'%s' not found" % arg
                if self.skip_errors:
                    print(_)
                    self.failed = True
                else:
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
        if self.dups_by_name or self.dups_by_hash:
            print("Duplicates detected!\n")
            if self.dups_by_name:
                print("Duplicates by name:\n")
                for basename in self.dups_by_name:
                    print("--\nbasename '{0}':".format(basename))
                    for filepath in sorted(self.dups_by_name[basename]):
                        print(filepath)
            if self.dups_by_hash:
                print("Duplicates by checksum:\n")
                for checksum in self.dups_by_hash:
                    print("--\nchecksum '{0}':".format(checksum))
                    for filepath in sorted(self.dups_by_hash[checksum]):
                        print(filepath)
            sys.exit(1)
        elif self.failed:
            sys.exit(2)
        else:
            print("No Duplicates Found")
            sys.exit(0)

    def check_path(self, path):
        if os.path.isfile(path):
            self.check_file(path)
        elif os.path.isdir(path):
            listing = []
            try:
                listing = os.listdir(path)
                listing = [x for x in listing if x[0] != '.']
            except OSError as _:
                print(_)
                self.failed = True
            for item in listing:
                subpath = os.path.join(path, item)
                if os.path.isdir(subpath):
                    self.check_path(subpath)
                else:
                    try:
                        self.is_file_dup(subpath)
                    except OSError as _:
                        log.error("error while checking file '{0}': {1}".format(subpath, _))
                        self.failed = True
        else:
            die("failed to determine if path '%s' is file or directory" % path)

    def is_file_dup(self, filepath):
        if os.path.islink(filepath):
            return False
        if self.is_file_dup_by_name(filepath):
            return True
        if self.is_file_dup_by_stats(filepath):
            return True
        return False

    def is_file_dup_by_name(self, filepath):
        basename = os.path.basename(filepath)
        if basename in self.files:
            self.dups_by_name[basename] = self.dups_by_name.get(basename, set())
            self.dups_by_name[basename].add(self.files[basename])
            self.dups_by_name[basename].add(filepath)
            return True
        else:
            self.files[basename] = filepath
        return False

    @staticmethod
    def hash(filepath):
        with open(filepath) as _:
            return hashlib.md5(_.read()).hexdigest()

    def is_file_dup_by_stats(self, filepath):
        size = os.stat(filepath).st_size
        if size == 0:
            return False
        checksum = None
        if size in self.sizes:
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
            for filepath in self.hashes[checksum]:
                self.dups_by_hash[checksum].add(filepath)
            return True
        return False


if __name__ == '__main__':
    FindDuplicateFiles().main()
