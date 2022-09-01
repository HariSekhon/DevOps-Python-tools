#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-12-19 18:19:34 +0000 (Thu, 19 Dec 2019)
#
#  https://github.com/HariSekhon/DevOps-Python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/HariSekhon
#

"""

Tool to convert XML to YAML

Reads any given files as XML and prints the equivalent YAML to stdout for piping or redirecting to a file.

Directories if given are detected and recursed, processing all files in the directory tree ending in a .xml suffix.

Works like a standard unix filter program - if no files are passed as arguments or '-' is passed then reads from
standard input.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import json
import os
import re
import sys
import xml
import xmltodict
import yaml
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, log, log_option
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1.0'


class XmlToYaml(CLI):

    def __init__(self):
        # Python 2.x
        super(XmlToYaml, self).__init__()
        # Python 3.x
        # super().__init__()
        self.indent = None
        self.re_xml_suffix = re.compile(r'.*\.xml$', re.I)

    def add_options(self):
        self.add_opt('-p', '--pretty', action='store_true', help='Pretty Print the resulting YAML')

    @staticmethod
    def xml_to_yaml(content, filepath=None):
        try:
            _ = xmltodict.parse(content)
        except xml.parsers.expat.ExpatError as _:
            file_detail = ''
            if filepath is not None:
                file_detail = ' in file \'{0}\''.format(filepath)
            die("Failed to parse XML{0}: {1}".format(file_detail, _))
        # xmltodict returns a unicode OrderedDict so need to make it a plain dict to come out properly not like:
        # !!python/object/apply:collections.OrderedDict
        yaml_string = yaml.safe_dump(json.loads(json.dumps(_)), encoding='utf-8', sort_keys=True)
        return yaml_string

    def run(self):
        if self.get_opt('pretty'):
            log_option('pretty', True)
            self.indent = 4
        if not self.args:
            self.args.append('-')
        for arg in self.args:
            if arg == '-':
                continue
            if not os.path.exists(arg):
                print("'{}' not found".format(arg))
                sys.exit(ERRORS['WARNING'])
            if os.path.isfile(arg):
                log_option('file', arg)
            elif os.path.isdir(arg):
                log_option('directory', arg)
            else:
                die("path '{}' could not be determined as either a file or directory".format(arg))
        for arg in self.args:
            self.process_path(arg)

    def process_path(self, path):
        if path == '-' or os.path.isfile(path):
            self.process_file(path)
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    if self.re_xml_suffix.match(filepath):
                        self.process_file(filepath)
        else:
            die("failed to determine if path '{}' is a file or directory".format(path))

    def process_file(self, filepath):
        log.debug("processing filepath '%s'", filepath)
        if filepath == '-':
            filepath = '<STDIN>'
        if filepath == '<STDIN>':
            print(self.xml_to_yaml(sys.stdin.read()))
        else:
            with open(filepath) as _:
                content = _.read()
                print(self.xml_to_yaml(content, filepath=filepath))


if __name__ == '__main__':
    XmlToYaml().main()
