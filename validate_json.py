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
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

"""

JSON Validator Tool

Does a simple validation of each file passed as an argument to this script.

First tries each file contents as a whole json document, if that fails validation or catches a memory error, then
it assumes the file contains multi-record format with one json document per line and tries an independent validation of
each line.

"""

from __future__ import print_function

__author__  = 'Hari Sekhon'
__version__ = '0.2'

import os
import sys
# using optparse rather than argparse for servers still on Python 2.6
sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])) + '/pylib')
try:
    from harisekhon.utils import *
    from harisekhon import CLI
except ImportError, e:
    print('module import failed: %s' % e, file=sys.stderr)
    sys.exit(4)

class JsonValidatorTool(CLI):

    def check_multiline_json(self):
            self.f.seek(0)
            for line in self.f:
                if not isJson(line):
                    if isJson(line.replace("'", '"')):
                        die(self.invalid_json_msg_single_quotes)
                    else:
                        die(self.invalid_json_msg)
            print('%s (multi-record format)' % self.valid_json_msg)
            return True

    def check_json(self, content):
        if isJson(content):
            print(self.valid_json_msg)
        elif isJson(content.replace("'", '"')):
            die(self.invalid_json_msg_single_quotes)
        elif self.check_multiline_json():
            pass
        else:
            die(self.invalid_json_msg)

    def run(self):
        if not self.args:
            self.usage()
        for filename in self.args:
            validate_file(filename)
        for self.filename in self.args:
            self.valid_json_msg   = '%s => JSON OK'      % self.filename
            self.invalid_json_msg = '%s => JSON INVALID' % self.filename
            self.invalid_json_msg_single_quotes = '%s (found single quotes not double quotes)' % self.invalid_json_msg
            mem_err = "file '%s', assuming Big Data multi-record json and re-trying validation line-by-line" % self.filename
            with open(self.filename) as self.f:
                content = None
                # most JSON files are fine to slurp like this
                # Big Data JSON files are json multi-record, will throw exception after running out of RAM and then be handled line by line
                try:
                    content = self.f.read()
                    try:
                        self.check_json(content)
                    except MemoryError:
                        print("memory error validating contents from %s" % mem_err)
                        self.check_multiline_json()
                except MemoryError:
                    print("memory error reading %s" % mem_err)
                    self.check_multiline_json()


if __name__ == '__main__':
    JsonValidatorTool().main()