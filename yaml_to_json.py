#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#  args: ../bash-tools/.gitlab-ci.yml
#
#  Author: Hari Sekhon
#  Date: 2020-08-18 01:17:56 +0100 (Tue, 18 Aug 2020)
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

Tool to convert YAML to JSON

Reads any given files as YAML and prints the equivalent JSON to stdout for piping or redirecting to a file.

Directories if given are detected and recursed, processing all files in the directory tree ending in a
.yml / .yaml suffix.

Works like a standard unix filter program - if no files are passed as arguments or '-' is passed then reads from
standard input.

Written to convert .gitlab-ci.yml files to JSON for inputting to the GitLab API for validation
(see gitlab_validate_ci_yml.sh in the DevOps-Bash-tools repo)

See also:

    yaml2json.sh - https://github.com/HariSekhon/DevOps-Bash-tools

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import json
import os
import re
import sys
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
__version__ = '0.2.0'


class YamlToJson(CLI):

    def __init__(self):
        # Python 2.x
        super(YamlToJson, self).__init__()
        # Python 3.x
        # super().__init__()
        self.re_yaml_suffix = re.compile(r'.*\.ya?ml$', re.I)

    @staticmethod
    def yaml_to_json(content, filepath=None):
        try:
            _ = yaml.load(content, Loader=yaml.FullLoader)
        except (KeyError, ValueError) as _:
            file_detail = ''
            if filepath is not None:
                file_detail = ' in file \'{0}\''.format(filepath)
            die("Failed to parse YAML{0}: {1}".format(file_detail, _))
        return json.dumps(_, sys.stdout, indent=4)

    def run(self):
        if not self.args:
            self.args.append('-')
        for arg in self.args:
            if arg == '-':
                continue
            if not os.path.exists(arg):
                print("'%s' not found" % arg)
                sys.exit(ERRORS['WARNING'])
            if os.path.isfile(arg):
                log_option('file', arg)
            elif os.path.isdir(arg):
                log_option('directory', arg)
            else:
                die("path '%s' could not be determined as either a file or directory" % arg)
        for arg in self.args:
            self.process_path(arg)

    def process_path(self, path):
        if path == '-' or os.path.isfile(path):
            self.process_file(path)
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    if self.re_yaml_suffix.match(filepath):
                        self.process_file(filepath)
        else:
            die("failed to determine if path '%s' is a file or directory" % path)

    def process_file(self, filepath):
        log.debug('processing filepath \'%s\'', filepath)
        if filepath == '-':
            filepath = '<STDIN>'
        if filepath == '<STDIN>':
            print(self.yaml_to_json(sys.stdin.read()))
        else:
            with open(filepath) as _:
                content = _.read()
                print(self.yaml_to_json(content, filepath=filepath))


if __name__ == '__main__':
    YamlToJson().main()
