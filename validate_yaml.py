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
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

"""

YAML Validator Tool

Validates each file passed as an argument

Directories are recursed, checking all files ending in a .yaml suffix.

Works like a standard unix filter program - if no files are passed as arguments or '-' is given then reads
from standard input

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import sys
import yaml
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, isYaml, vlog_option, uniq_list_ordered
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.7.3'

class YamlValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(YamlValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.re_yaml_suffix = re.compile(r'.*\.ya?ml$', re.I)
        self.valid_yaml_msg = '<unknown> => YAML OK'
        self.invalid_yaml_msg = '<unknown> => YAML INVALID'
        self.failed = False

    # def check_multiline_yaml(self):
    #         self.f.seek(0)
    #         for line in self.f:
    #             if not isYaml(line):
    #                 die(self.invalid_yaml_msg)
    #         print('%s (multi-record format)' % self.valid_yaml_msg)
    #         return True

    def check_yaml(self, content):
        if isYaml(content):
            if self.options.print:
                print(content, end='')
            else:
                print(self.valid_yaml_msg)
        # multi-record yaml like JSON in Big Data isn't really used
        # elif self.check_multiline_yaml():
        #     pass
        else:
            self.failed = True
            if not self.options.print:
                if self.get_verbose() > 2:
                    try:
                        yaml.load(content)
                    except yaml.YAMLError as _:
                        print(_)
                die(self.invalid_yaml_msg)

    def add_options(self):
        self.add_opt('-p', '--print', action='store_true',
                     help='Print the YAML document(s) if valid, else print nothing (useful for shell ' +
                     'pipelines). Exit codes are still 0 for success, or %s for failure'
                     % ERRORS['CRITICAL'])

    def run(self):
        if not self.args:
            self.args.append('-')
        args = uniq_list_ordered(self.args)
        for arg in args:
            if arg == '-':
                continue
            if not os.path.exists(arg):
                print("'%s' not found" % arg)
                sys.exit(ERRORS['WARNING'])
            if os.path.isfile(arg):
                vlog_option('file', arg)
            elif os.path.isdir(arg):
                vlog_option('directory', arg)
            else:
                die("path '%s' could not be determined as either a file or directory" % arg)
        for arg in args:
            self.check_path(arg)
        if self.failed:
            sys.exit(ERRORS['CRITICAL'])

    def check_path(self, path):
        if path == '-' or os.path.isfile(path):
            self.check_file(path)
        elif os.path.isdir(path):
            for item in os.listdir(path):
                subpath = os.path.join(path, item)
                if os.path.isdir(subpath):
                    self.check_path(subpath)
                elif self.re_yaml_suffix.match(item):
                    self.check_file(subpath)
        else:
            die("failed to determine if path '%s' is file or directory" % path)

    def check_file(self, filename):
        if filename == '-':
            filename = '<STDIN>'
        self.valid_yaml_msg = '%s => YAML OK' % filename
        self.invalid_yaml_msg = '%s => YAML INVALID' % filename
        if filename == '<STDIN>':
            self.check_yaml(sys.stdin.read())
        else:
            try:
                with open(filename) as iostream:
                    self.check_yaml(iostream.read())
            except IOError as _:
                die("ERROR: %s" % _)


if __name__ == '__main__':
    YamlValidatorTool().main()
