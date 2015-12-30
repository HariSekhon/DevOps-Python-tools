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

XML Validator Tool

Does a simple validation of each file passed as an argument to this script.

Works like a standard unix filter program - if no files are passed as arguments or '-' is passed then reads from standard input

"""

# Forked from validate_yaml.py

from __future__ import print_function

__author__  = 'Hari Sekhon'
__version__ = '0.3'

import os
import sys
import traceback
import xml.etree.ElementTree as ET
sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])) + '/pylib')
try:
    from harisekhon.utils import *
    from harisekhon import CLI
except ImportError, e:
    print('module import failed: %s' % e, file=sys.stderr)
    sys.exit(4)


class XmlValidatorTool(CLI):

    def check_xml(self, content):
        if isXml(content):
            print(self.valid_xml_msg)
        else:
            # TODO: change this to use a getter
            if self.options.verbose > 2:
                try:
                    ET.fromstring(content)
                except ET.ParseError, e:
                    print(e)
            die(self.invalid_xml_msg)

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
            self.valid_xml_msg   = '%s => XML OK'      % filename
            self.invalid_xml_msg = '%s => XML INVALID' % filename
            if filename == '<STDIN>':
                self.check_xml(sys.stdin.read())
            else:
                with open(filename) as self.f:
                    self.check_xml(self.f.read())


if __name__ == '__main__':
    XmlValidatorTool().main()
