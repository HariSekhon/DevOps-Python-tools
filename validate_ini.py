#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-09-15 15:29:39 +0200 (Fri, 15 Sep 2017)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

INI file Validator Tool

Validates each file passed as an argument

Directories are recursed, checking all files ending in a .ini or .properties suffix.

Works like a standard unix filter program - if no files are passed as arguments or '-' is given then reads
from standard input

Also checks for duplicate sections and keys within a section in INI and Java property files

Written to be able to test Presto, Drill and Ambari property files for Continuous Integration and tested against a wide
variety of different ini and properties files both in this repo (see tests/) and in the master Dockerfiles repo which
contains lots of DockerHub image source builds and configurations for a wide variety of official Big Data open source
technologies

See also validate_ini2.py which uses Python's native ConfigParser / configparser (Python 2 / Python 3)
but gives much less depth, flexibility and control to allow for different variations of ini files than this version

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# from __future__ import unicode_literals

import os
import re
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, log_option, uniq_list_ordered, log, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.12.2'


class IniValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(IniValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.filename = None
        self.re_suffix = re.compile(r'.*\.(?:ini|properties)$', re.I)
        # In Windows ini key cannot contain equals sign = or semicolon ;
        #                                   key=val or [section]
        self.re_ini_section = re.compile(r'^\s*\[([\w=\:\.-]+)\]\s*$')
        self.re_ini_key = re.compile(r'^\s*(?:[^\[;=]+)s*$')
        # INI value can be anything .* so not regex'ing it
        self.valid_ini_msg = '<unknown> => INI OK'
        self.invalid_ini_msg = '<unknown> => INI INVALID'
        self.opts = {}
        self.failed = False
        self.include = None
        self.exclude = None
        self.section = ''
        # global section is represented by blank key
        self.sections = {
            '': {}
        }

    def add_options(self):
        self.add_opt('-a', '--no-hash-comments', action='store_true',
                     help="Disallow hash comments (default is to allow because they're so common in unix files)")
        self.add_opt('-c', '--allow-colon-delimiters', action='store_true',
                     help='Allow colons as delimiters instead of equals signs')
        # Refused to enable this options until upstream zookeeper 3.4.8 log4j.properties ended up with duplicate keys
        # better than --exclude entirely
        self.add_opt('-s', '--ignore-duplicate-sections', action='store_true',
                     help='Ignore duplicate sections (sloppy and not recommended but better than --exclude sometimes)')
        self.add_opt('-k', '--ignore-duplicate-keys', action='store_true',
                     help='Ignore duplicate keys inside the same section (not recommended but better than --exclude)')
        #self.add_opt('-i', '--no-inline-comments', action='store_true',
        #             help='Do not allow inline comments, must be on their own lines (WinAPI function reqires this)')
        self.add_opt('-E', '--allow-empty', action='store_true', help='Permit files with no keys or sections')
        self.add_opt('-b', '--no-blank-lines', action='store_true',
                     help='Do not allow blank lines as some rudimentary programs expect to not allow them')
        self.add_opt('-p', '--print', action='store_true',
                     help='Print the INI lines(s) which are valid, else print nothing (useful for shell ' + \
                    'pipelines). Exit codes are still 0 for success, or {0} for failure'.format(ERRORS['CRITICAL']))
        self.add_opt('-i', '--include', metavar='regex', default=os.getenv('INCLUDE'),
                     help='Regex of file / directory paths to check only ones that match ($INCLUDE, case insensitive)')
        self.add_opt('-e', '--exclude', metavar='regex', default=os.getenv('EXCLUDE'),
                     help='Regex of file / directory paths to exclude from checking, ' + \
                          '($EXCLUDE, case insensitive, takes priority over --include)')

    def process_options(self):
        self.opts = {
            'no_hashes': self.get_opt('no_hash_comments'),
            'allow_colons': self.get_opt('allow_colon_delimiters'),
            'allow_empty': self.get_opt('allow_empty'),
            #'disallow_inline_comments': self.get_opt('disallow_inline_comments'),
            'ignore_duplicate_sections': self.get_opt('ignore_duplicate_sections'),
            'ignore_duplicate_keys': self.get_opt('ignore_duplicate_keys'),
            'disallow_blanks': self.get_opt('no_blank_lines'),
            'print': self.get_opt('print')
        }
        self.include = self.get_opt('include')
        self.exclude = self.get_opt('exclude')
        if self.include:
            validate_regex(self.include, 'include')
            self.include = re.compile(self.include, re.I)
        if self.exclude:
            validate_regex(self.exclude, 'exclude')
            self.exclude = re.compile(self.exclude, re.I)
        for key in self.opts:
            log_option(key, self.opts[key])

    def is_included(self, path):
        if self.include:
            if self.include.search(path):
                log.debug("including path: %s", path)
                return True
            log.debug("not including path: %s", path)
            return False
        return True

    def is_excluded(self, path):
        if self.exclude and self.exclude.search(path):
            log.debug("excluding path: %s", path)
            return True
        return False

    def strip_comments(self, line, comment_count):
        found_comment = False
        if ';' in line:
            line = line.split(';', 1)[0]
            found_comment = True
        if not self.opts['no_hashes'] and '#' in line:
            line = line.split('#', 1)[0]
            found_comment = True
        if found_comment:
            comment_count += 1
        return (line, comment_count)

    def get_key_value(self, line):
        key = None
        value = None
        # must differentiate colon format INI lines with equals symbol in value
        # (since .+ is valid for ini values)
        if not self.opts['allow_colons']:
            if '=' in line:
                (key, value) = line.split('=', 1)
        else:
            if ':' in line:
                (key, value) = line.split(':', 1)
        return (key, value)

    def process_section(self, line):
        match = self.re_ini_section.match(line)
        if match:
            self.section = match.group(1)
            if self.section in self.sections and not self.opts['ignore_duplicate_sections']:
                log.debug("failing ini due to duplicate sections '%s'", self.section)
                raise AssertionError("duplicate sections '%s'" % self.section)
            # be careful here as we may now optionally allow duplicate sections
            if self.section not in self.sections:
                self.sections[self.section] = {}
        else:
            log.debug("failing ini due to invalid section on line: %s", line)
            raise AssertionError("invalid section on line: %s" % line)

    def process_key_value(self, line, key, value):
        if not self.re_ini_key.match(key):
            log.debug("failing ini due to invalid key '%s' in line: %s", key, line)
            raise AssertionError("invalid key '%s' in line: %s" % (key, line))
        elif key in self.sections[self.section].keys() and not self.opts['ignore_duplicate_keys']:
            log.debug("failing ini due to duplicate key '%s' in section '%s' " +
                      "detected in line: %s", key, self.section, line)
            raise AssertionError("duplicate key '%s' in section '%s'" % (key, self.section))
        self.sections[self.section][key] = value

    def process_ini(self, filehandle):
        variable_count = 0
        comment_count = 0
        blank_count = 0
        self.section = ''
        self.sections = {
            '': {}
        }
        for line in filehandle:
            if not line.strip():
                if self.opts['disallow_blanks']:
                    log.debug('failing ini due to blank line detected')
                    raise AssertionError('blank line detected')
                blank_count += 1
                continue
            (line, comment_count) = self.strip_comments(line, comment_count)
            if not line.strip():
                continue
            # short circuit on more common key=value first before trying [section]
            (key, value) = self.get_key_value(line)
            if key:
                self.process_key_value(line, key, value)
            elif '[' in line:
                self.process_section(line)
            else:
                log.debug('failing ini due to no key or section detected for line: %s', line)
                raise AssertionError('no key or section detected for line: %s' % line)
            variable_count += 1
        if variable_count < 1 and not self.opts['allow_empty']:
            raise AssertionError('no keys or sections found')
        count = variable_count + comment_count + blank_count
        log.debug('%s INI lines passed (%s variables, %s comments, %s blank lines)', \
                  count, variable_count, comment_count, blank_count)

    def check_ini(self, filehandle):
        try:
            self.process_ini(filehandle)
            if self.opts['print']:
                filehandle.seek(0)
                print(filehandle.read(), end='')
            else:
                print(self.valid_ini_msg)
        except AssertionError as _:
            self.failed = True
            if not self.opts['print']:
                die('{0}: {1}'.format(self.invalid_ini_msg, _))

    def run(self):
        if not self.args:
            self.args.append('-')
        args = uniq_list_ordered(self.args)
        for arg in args:
            if arg == '-':
                continue
            if not os.path.exists(arg):
                print("'{0}' not found".format(arg))
                sys.exit(ERRORS['CRITICAL'])
            if os.path.isfile(arg):
                log_option('file', arg)
            elif os.path.isdir(arg):
                log_option('directory', os.path.abspath(arg))
            else:
                die("path '{0}' could not be determined as either a file or directory".format(arg))
        for arg in args:
            self.check_path(arg)
        if self.failed:
            sys.exit(ERRORS['CRITICAL'])

    def check_path(self, path):
        if path == '-' or os.path.isfile(path):
            self.check_file(path)
        elif os.path.isdir(path):
            self.walk(path)
        else:
            die("failed to determine if path '%s' is file or directory" % path)

    # don't need to recurse when using walk generator
    def walk(self, path):
        if self.is_excluded(path):
            return
        for root, dirs, files in os.walk(path, topdown=True):
            # modify dirs in place to prune descent for increased efficiency
            # requires topdown=True
            # calling is_excluded() on joined root/dir so that things like
            #   '/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+' will match
            dirs[:] = [d for d in dirs if not self.is_excluded(os.path.join(root, d))]
            for filename in files:
                file_path = os.path.join(root, filename)
                if self.re_suffix.match(file_path):
                    self.check_file(file_path)

    def check_file(self, filename):
        self.filename = filename
        if self.filename == '-':
            self.filename = '<STDIN>'
        self.valid_ini_msg = '%s => INI OK' % self.filename
        self.invalid_ini_msg = '%s => INI INVALID' % self.filename
        if self.filename == '<STDIN>':
            log.debug('ini stdin')
            # TODO: should technically write to temp file to be able to seek(0) for print mode
            self.check_ini(sys.stdin)
        else:
            if self.is_excluded(filename):
                return
            if not self.is_included(filename):
                return
            log.debug('checking %s', self.filename)
            try:
                with open(self.filename) as iostream:
                    self.check_ini(iostream)
            except IOError as _:
                die("ERROR: %s" % _)


if __name__ == '__main__':
    IniValidatorTool().main()
