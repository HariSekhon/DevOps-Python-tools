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

YAML Validator Tool

Does a simple validation of each file passed as an argument to this script.

"""

# Forked from validate_yaml.py

from __future__ import print_function

__author__  = 'Hari Sekhon'
__version__ = '0.2'

import os
import sys
import yaml
sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])) + '/pylib')
try:
    from harisekhon.utils import *
    from harisekhon import CLI
except ImportError, e:
    print('module import failed: %s' % e, file=sys.stderr)
    sys.exit(4)


class YamlValidatorTool(CLI):

    def check_multiline_yaml(self):
            self.f.seek(0)
            for line in self.f:
                if not isYaml(line):
                    die(self.invalid_yaml_msg)
            print('%s (multi-record format)' % self.valid_yaml_msg)
            return True

    def check_yaml(self, content):
        if isYaml(content):
            print(self.valid_yaml_msg)
        # multi-record yaml like in Big Data isn't really used like with JSON
        # elif self.check_multiline_yaml():
        #     pass
        else:
            # TODO: change this to use a getter
            if self.options.verbose > 2:
                yaml.load(content)
            die(self.invalid_yaml_msg)

    def run(self):
        if not self.args:
            self.usage()
        for filename in self.args:
            validate_file(filename)
        for self.filename in self.args:
            self.valid_yaml_msg   = '%s => YAML OK'      % self.filename
            self.invalid_yaml_msg = '%s => YAML INVALID' % self.filename
            # self.invalid_yaml_msg_single_quotes = '%s (found single quotes not double quotes)' % self.invalid_yaml_msg
            # mem_err = "file '%s', assuming Big Data multi-record yaml and re-trying validation line-by-line" % self.filename
            with open(self.filename) as self.f:
                # content = None
                # most JSON files are fine to slurp like this
                # Big Data JSON files are yaml multi-record, will throw exception after running out of RAM and then be handled line by line
                # try:
                #     content = self.f.read()
                #     try:
                #         self.check_yaml(content)
                #     except MemoryError:
                #         print("memory error validating contents from %s" % mem_err)
                #         self.check_multiline_yaml()
                # except MemoryError:
                #     print("memory error reading %s" % mem_err)
                #     self.check_multiline_yaml()
                self.check_yaml(self.f.read())


if __name__ == '__main__':
    YamlValidatorTool().main()