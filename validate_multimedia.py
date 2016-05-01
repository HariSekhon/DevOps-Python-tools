#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-05-01 20:46:56 +0100 (Sun, 01 May 2016)
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

Media File Validator Tool

Validates each file passed as an argument using ffmpeg or ffprobe (for --quick mode). ffmpeg / ffprobe must be in $PATH

Directories are recursed, checking any files ending in one of the following extensions:

.mp3
.mp4
.mpg
.mpeg
.avi
.mkv

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import sys
import subprocess
from subprocess import CalledProcessError
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import die, ERRORS, log, log_option, uniq_list_ordered, which
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.7.4'

class MediaValidatorTool(CLI):

    def __init__(self):
        # Python 2.x
        super(MediaValidatorTool, self).__init__()
        # Python 3.x
        # super().__init__()
        self.re_media_suffix = re.compile(r'.*\.(?:mp[34]|mpe?g|avi|mkv|flv)$', re.I)
        self.failed = False
        self.validate_cmd = "ffmpeg -v error -f null - -i"

    def add_options(self):
        self.add_opt('-q', '--quick', action='store_true',
                     help="Quick mode (uses 'ffprobe' instead of 'ffmpeg')")
        self.add_opt('-c', '--continue', action='store_true',
                     help='Continue after finding a broken multimedia file if recursing a directory tree')

    def run(self):
        if self.get_opt('quick'):
            log_option('quick', self.get_opt('quick'))
            self.validate_cmd = "ffprobe"
        if not which(self.validate_cmd.split()[0]):
            die('ffmpeg / ffprobe not found in $PATH')
        args = uniq_list_ordered(self.args)
        for arg in args:
            if not os.path.exists(arg):
                print("'%s' not found" % arg)
                sys.exit(ERRORS['WARNING'])
            if os.path.isfile(arg):
                log_option('file', arg)
            elif os.path.isdir(arg):
                log_option('directory', arg)
            else:
                die("path '%s' could not be determined as either a file or directory" % arg)
        for arg in args:
            self.check_path(arg)
        if self.failed:
            sys.exit(ERRORS['CRITICAL'])
        if self.failed:
            sys.exit(1)

    def check_path(self, path):
        if os.path.isfile(path):
            self.check_media_file(path)
        elif os.path.isdir(path):
            for item in os.listdir(path):
                subpath = os.path.join(path, item)
                if os.path.isdir(subpath):
                    self.check_path(subpath)
                elif self.re_media_suffix.match(item):
                    self.check_media_file(subpath)
        else:
            die("failed to determine if path '%s' is file or directory" % path)

    def check_media_file(self, filename):
        valid_media_msg = '%s => OK' % filename
        invalid_media_msg = '%s => INVALID' % filename
        # method for checking this comes from:
        # http://superuser.com/questions/100288/how-can-i-check-the-integrity-of-a-video-file-avi-mpeg-mp4
        try:
            # cmd = self.validate_cmd.format(filename)
            cmd = self.validate_cmd
            log.debug('cmd: %s %s', cmd, filename)
            log.info('verifying {0}'.format(filename))
            # capturing stderr to stdout because ffprobe prints to stderr in all cases
            subprocess.check_output(cmd.split() + [filename], stderr=subprocess.STDOUT)
            print(valid_media_msg)
        except CalledProcessError as _:
            if self.verbose > 2:
                print(_.output)
            if self.get_opt('continue'):
                self.failed = True
                return False
            die(invalid_media_msg)


if __name__ == '__main__':
    MediaValidatorTool().main()
