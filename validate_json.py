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

Works like a standard unix filter program - if no files are passed as arguments or '-' is passed then reads from
standard input (--multi-line must be specified explicitly if feeding to stdin as can't rewind the standard input
stream to test for multi-line on a second pass).

"""

from __future__ import print_function

__author__  = 'Hari Sekhon'
__version__ = '0.3'

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])) + '/pylib')
try:
    from harisekhon.utils import *
    from harisekhon import CLI
except ImportError, e:
    print('module import failed: %s' % e, file=sys.stderr)
    sys.exit(4)

class JsonValidatorTool(CLI):

    def add_options(self):
        self.parser.add_option('-m', '--multi-record', action='store_true',
                               help='Test explicitly for multi-record JSON data, where each line is a separate json ' \
                                  + 'document separated by newlines. Must use if reading multi-record json format ' \
                                  + 'on standard input')

    def check_mutlirecord_json(self):
            for line in self.f:
                if not isJson(line):
                    if isJson(line.replace("'", '"')):
                        die('%s (multi-record format)' % self.invalid_json_msg_single_quotes)
                    else:
                        return False
            print('%s (multi-record format)' % self.valid_json_msg)
            return True

    def check_json(self, content):
        if isJson(content):
            print(self.valid_json_msg)
        elif isJson(content.replace("'", '"')):
            die(self.invalid_json_msg_single_quotes)
        else:
            if self.f is not sys.stdin:
                self.f.seek(0)
                if self.check_mutlirecord_json():
                    return True
            # pointless since it would simply return 'ValueError: No JSON object could be decoded'
            # TODO: replace with a getter
            # if self.options.verbose > 2:
                # try:
                #     json.loads(content)
                # except Exception, e:
                #     print(e)
            die(self.invalid_json_msg)

    def run(self):
        if not self.args:
            self.args.append('-')
        for filename in self.args:
            if filename == '-':
                continue
            validate_file(filename)
        for filename in self.args:
            if filename == '-':
                filename = '<STDIN>'
            self.valid_json_msg   = '%s => JSON OK'      % filename
            self.invalid_json_msg = '%s => JSON INVALID' % filename
            self.invalid_json_msg_single_quotes = '%s (found single quotes not double quotes)' % self.invalid_json_msg
            mem_err = "file '%s', assuming Big Data multi-record json and re-trying validation line-by-line" % filename
            if filename == '<STDIN>':
                self.f = sys.stdin
                if self.options.multi_record:
                    if not self.check_mutlirecord_json():
                        die(self.invalid_json_msg)
                else:
                    self.check_json(sys.stdin.read())
            else:
                with open(filename) as self.f:
                    if self.options.multi_record:
                        self.check_mutlirecord_json()
                    else:
                        # most JSON files are fine to slurp like this
                        # Big Data JSON files are json multi-record, will throw exception after running out of RAM and then be handled line by line
                        try:
                            content = self.f.read()
                            try:
                                self.check_json(content)
                            except MemoryError:
                                print("memory error validating contents from %s" % mem_err)
                                f.seek(0)
                                self.check_mutlirecord_json()
                        except MemoryError:
                            print("memory error reading %s" % mem_err)
                            f.seek(0)
                            self.check_mutlirecord_json()


if __name__ == '__main__':
    JsonValidatorTool().main()