#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-05-01 20:46:56 +0100 (Sun, 01 May 2016)
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

Media File Validator Tool

Validates each file passed as an argument using ffmpeg or ffprobe (for --quick mode). ffmpeg / ffprobe must be in $PATH

Directories are recursed, checking any files ending in one of the following extensions:

.mp3
.mp4
.mpg
.mpeg
.m4a
.avi
.mkv
.wmv

or if given a --regex will check any matching filenames in the directories given. Files explicitly given on the
command line are always checked.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import os
import re
import sys
import subprocess
CalledProcessError = subprocess.CalledProcessError
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, log, log_option, uniq_list_ordered, which, validate_regex
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.7.8'

class MediaValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(MediaValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.failed = False
        self.re_media_suffix = re.compile(r'.*\.(?:mp[34]|mpe?g|m4a|avi|flv|mkv|wmv)$', re.I)
        self.skip_errors = None
        self.quick = None
        self.regex = None
        self.timeout_default = 0
        # method for checking this comes from:
        # http://superuser.com/questions/100288/how-can-i-check-the-integrity-of-a-video-file-avi-mpeg-mp4
        self.validate_cmd = "ffmpeg -v error -f null - -i"

    def add_options(self):
        self.add_opt('-r', '--regex', default=None,
                     help='Regex of files to check when recursing a directory ' +
                     '(case insensitive, replaces extension check)')
        self.add_opt('-q', '--quick', action='store_true', default=False,
                     help="Quick mode (uses 'ffprobe' instead of 'ffmpeg')")
        self.add_opt('-c', '--continue', action='store_true', default=False,
                     help='Continue checking remaining files after finding a broken multimedia file')

    def process_args(self):
        self.skip_errors = self.get_opt('continue')
        self.quick = self.get_opt('quick')
        self.regex = self.get_opt('regex')
        args = uniq_list_ordered(self.args)
        if not args:
            self.usage('no files/dirs specified')
        log_option('files/dirs', args)
        log_option('regex', self.regex)
        log_option('quick', self.quick)
        log_option('continue-on-error', self.skip_errors)
        if self.regex:
            validate_regex(self.regex)
            self.regex = re.compile(self.regex, re.I)
        if self.quick:
            self.validate_cmd = 'ffprobe'
        if not which(self.validate_cmd.split()[0]):
            die('ffmpeg / ffprobe not found in $PATH')
        return args

    def run(self):
        args = self.process_args()
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
                log_option('directory', os.path.abspath(arg))
            else:
                die("path '%s' could not be determined as either a file or directory" % arg)
        for arg in args:
            try:
                self.check_path(arg)
            except OSError as _:
                if self.skip_errors:
                    print(_)
                    self.failed = True
                else:
                    die(_)
        if self.failed:
            sys.exit(2)

    def check_path(self, path):
        if os.path.isfile(path):
            # files given explicitly are checked regardless
            # if self.regex and self.regex.search(path):
            self.check_media_file(path)
        elif os.path.isdir(path):
            listing = []
            try:
                listing = os.listdir(path)
                listing = [x for x in listing if x[0] != '.']
            except OSError as _:
                if self.skip_errors:
                    print(_)
                    self.failed = True
                else:
                    die(_)
            for item in listing:
                subpath = os.path.join(path, item)
                if os.path.isdir(subpath):
                    self.check_path(subpath)
                elif self.regex:
                    if self.regex.search(item):
                        self.check_media_file(subpath)
                elif self.re_media_suffix.match(item):
                    self.check_media_file(subpath)
        else:
            die("failed to determine if path '%s' is file or directory" % path)

    def check_media_file(self, filename):
        #if self.is_excluded(filename):
        #    return
        valid_media_msg = '%s => OK' % filename
        invalid_media_msg = '%s => INVALID' % filename
        cmd = self.validate_cmd
        log.debug('cmd: %s %s', cmd, filename)
        log.info('verifying {0}'.format(filename))
        # cmd = self.validate_cmd.format(filename)
        try:
            # capturing stderr to stdout because ffprobe prints to stderr in all cases
            # Python 2.7+
            #subprocess.check_output(cmd.split() + [filename], stderr=subprocess.STDOUT)
            proc = subprocess.Popen(cmd.split() + [filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (stdout, _) = proc.communicate()
            returncode = proc.wait()
            if returncode != 0 or (stdout is not None and 'Error' in stdout):
                _ = CalledProcessError(returncode, cmd)
                _.output = stdout
                raise _
            print(valid_media_msg)
        except CalledProcessError as _:
            if self.verbose > 2:
                print(_.output)
            if self.skip_errors:
                print(invalid_media_msg)
                self.failed = True
                return False
            die(invalid_media_msg)
        except OSError as _:
            die("OSError: '{0}' when running '{1} {2}'", _, cmd, filename)


if __name__ == '__main__':
    MediaValidatorTool().main()
