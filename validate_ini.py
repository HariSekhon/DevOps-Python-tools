#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-09-15 15:29:39 +0200 (Fri, 15 Sep 2017)
#
#  https://github.com/harisekhon/pytools
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
__version__ = '0.5.0'


# could consider using ConfigParser in Python2 / configparser in Python3
# but this gives more control over validation rules

class IniValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(IniValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.filename = None
        self.re_ini_suffix = re.compile(r'\.(?:ini|properties)$', re.I)
        # In Windows ini key cannot contain equals sign = or semicolon ;
        #                                   key=val or [section]
        self.re_ini_section = re.compile(r'^\s*\[([\w=\:\.-]+)\]\s*$')
        self.re_ini_key = re.compile(r'^\s*(?:[^\[;=]+)s*$')
        # INI value can be anything .* so not regex'ing it
        self.valid_ini_msg = '<unknown> => INI OK'
        self.invalid_ini_msg = '<unknown> => INI INVALID'
        self.opts = {}
        self.failed = False
        self.exclude = None

    def add_options(self):
        self.add_opt('-a', '--allow-hash-comments', action='store_true',
                     help='Allow hash comments as well as semicolons')
        self.add_opt('-c', '--allow-colon-delimiters', action='store_true',
                     help='Allow colons as delimiters instead of equals signs')
        # this should never be valid, always enforce no duplicates
        #self.add_opt('-d', '--no-duplicate-keys', action='store_true',
        #             help='Do not allow duplicate sections or duplicate keys inside the same section')
        #self.add_opt('-i', '--no-inline-comments', action='store_true',
        #             help='Do not allow inline comments, must be on their own lines (WinAPI function reqires this)')
        self.add_opt('-b', '--no-blanks', action='store_true',
                     help='Do not allow blank lines as some programs do not allow them' + \
                          ' (some rudimentary programs do not allow this)')
        self.add_opt('-p', '--print', action='store_true',
                     help='Print the INI lines(s) which are valid, else print nothing (useful for shell ' + \
                    'pipelines). Exit codes are still 0 for success, or {0} for failure'.format(ERRORS['CRITICAL']))
        self.add_opt('-e', '--exclude', metavar='regex', default=os.getenv('EXCLUDE'),
                     help='Regex of file / directory paths to exclude from checking ($EXCLUDE)')

    def process_options(self):
        self.opts = {
            'allow_hashes': self.get_opt('allow_hash_comments'),
            'allow_colons': self.get_opt('allow_colon_delimiters'),
            #'disallow_inline_comments': self.get_opt('disallow_inline_comments'),
            'disallow_blanks': self.get_opt('no_blanks'),
            'print': self.get_opt('print')
        }
        self.exclude = self.get_opt('exclude')
        if self.exclude:
            validate_regex(self.exclude, 'exclude')
            self.exclude = re.compile(self.exclude, re.I)

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
        if self.opts['allow_hashes'] and '#' in line:
            line = line.split('#', 1)[0]
            found_comment = True
        if found_comment:
            comment_count += 1
        return (line, comment_count)

    def process_ini(self, filehandle):
        variable_count = 0
        comment_count = 0
        blank_count = 0
        section = ''
        sections = {
            # global section is represented by blank key
            '': {}
        }
        for line in filehandle:
            if not line.strip():
                if self.opts['disallow_blanks']:
                    log.debug('failing ini due to blank line detected')
                    return False
                blank_count += 1
                continue
            (line, comment_count) = self.strip_comments(line, comment_count)
            if not line.strip():
                continue
            # short circuit on more common key=value first before trying [section]
            #if self.re_ini_key_value.match(line):
            #    pass
            # XXX: potential BUG: how to differentiate colon format INI lines with equals in value
            # (since .+ is valid for ini values)
            if '=' in line:
                (key, value) = line.split('=', 1)
                if not self.re_ini_key.match(key):
                    log.debug("failing ini due to invalid key '%s' in line: %s", key, line)
                    return False
                # always enforce no duplicates
                elif key in sections[section]:
                    log.debug("failing ini due to duplicate key '%s' in section '%s' " +
                              "detected in line: %s", key, section, line)
                    return False
                sections[section][key] = value
            elif self.opts['allow_colons'] and ':' in line:
                (key, value) = line.split(':', 1)
                if not self.re_ini_key.match(key):
                    log.debug("failing ini due to invalid key '%s' in colon separated ini line: %s", key, line)
                    return False
                # always enforce no duplicates
                if key in sections[section]:
                    log.debug("failing ini due to duplicate key '%s' in section '%s' " +
                              "of colon separated ini line: %s", key, section, line)
                    return False
                sections[section][key] = value
            elif '[' in line:
                match = self.re_ini_section.match(line)
                if match:
                    section = match.group(1)
                    if section in sections:
                        log.debug("failing ini due to duplicate sections '%s'", section)
                        return False
                    # valid [section] and not duplicate if reaches this point
                    sections[section] = {}
                else:
                    log.debug('failing ini due to invalid section')
                    return False
            else:
                log.debug('failing ini due to no key or section detected for line: %s', line)
                return False
            variable_count += 1
        if variable_count < 1:
            return False
        count = variable_count + comment_count + blank_count
        log.debug('%s INI lines passed (%s variables, %s comments, %s blank lines', \
                  count, variable_count, comment_count, blank_count)
        return True

    def check_ini(self, filehandle):
        if self.process_ini(filehandle):
            if self.opts['print']:
                filehandle.seek(0)
                print(filehandle.read(), end='')
            else:
                print(self.valid_ini_msg)
        else:
            self.failed = True
            if not self.opts['print']:
                die(self.invalid_ini_msg)

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
                log_option('directory', arg)
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
                if self.re_ini_suffix.match(file_path):
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
            log.debug('checking %s', self.filename)
            try:
                with open(self.filename) as iostream:
                    self.check_ini(iostream)
            except IOError as _:
                die("ERROR: %s" % _)


if __name__ == '__main__':
    IniValidatorTool().main()
