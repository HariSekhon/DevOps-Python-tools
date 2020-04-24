#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2009-12-09 19:58:14 +0000 (Wed, 09 Dec 2009)
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
Prints a slick welcome message with last login time

Tested on Mac OS X and Linux
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# from __future__ import unicode_literals

import getpass
import os
import random
import re
import string
import sys
import time
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import ERRORS, isUser, which, printerr
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '2.0.4'


class Welcome(CLI):

    def __init__(self):
        # Python 2.x
        super(Welcome, self).__init__()
        # Python 3.x
        # super().__init__()
        self.quick = False
        self.timeout_default = 20

    @staticmethod
    def titlecase_user(user):
        if user == 'root':
            user = user.upper()
        elif len(user) < 4 or re.search(r'\d', user):
            # probably not a real name
            pass
        else:
            user = user.title()
        return user

    def construct_msg(self):
        # user = os.getenv('USER', '').strip()
        user = getpass.getuser()
        if not isUser(user):
            # print("invalid user '%s' determined from environment variable $USER, failed regex validation" % user)
            print("invalid user '%s' returned by getpass.getuser(), failed regex validation" % user)
            sys.exit(ERRORS['CRITICAL'])
        user = self.titlecase_user(user)
        msg = 'Welcome %s - ' % user
        last = ''
        if which("last"):
            _ = os.popen('last -100')
            _.readline()
            re_skip = re.compile(r'^(?:reboot|wtmp)|^\s*$')
            last = ''
            for line in _:
                last = line.rstrip('\n')
                if re_skip.match(last):
                    last = ''
                    continue
                break
            _.close()
        else:
            printerr("WARNING: 'last' command not found, will not be able to get last login information")
        if last:
            msg += 'last login was '
            last_user = re.sub(r'\s+.*$', '', last)
            if last_user == 'root':
                last_user = 'ROOT'
            # strip up to "Day Mon NN" ie "%a %b %e ..."
            (last, num_replacements) = re.subn(r'.*(\w{3}\s+\w{3}\s+\d+)', r'\g<1>', last)
            if not num_replacements:
                print('failed to find the date format in the last log')
                sys.exit(ERRORS['CRITICAL'])
            last = re.sub(' *$', '', last)
            if last_user == 'ROOT':
                msg += 'ROOT'
            elif last_user.lower() == user.lower():
                msg += 'by you'
            else:
                msg += 'by %s' % last_user
            msg += ' => %s' % last
        else:
            msg += 'no last login information available!'
        return msg

    def print_welcome(self):
        msg = self.construct_msg()
        if self.quick:
            print(msg)
            return
        try:
            charmap = list(string.ascii_uppercase + string.ascii_lowercase + '@#$%^&*()')
            # print '',
            # print('', end='')
            for i in range(0, len(msg)):
                char = msg[i]
                # print '',
                print(' ', end='')
                j = 0
                while 1:
                    if j > 3:
                        random_char = char
                    else:
                        random_char = random.choice(charmap)
                    # going from print statement to func requires one less backspace otherwise it scrolls backwards
                    # print '\b\b%s' % random_char,
                    print('\b%s' % random_char, end='')
                    sys.stdout.flush()
                    if char == random_char:
                        break
                    j += 1
                    time.sleep(0.0085)
            print()
        except KeyboardInterrupt:
            # print('\b\b\b\b%s' % msg[i:])
            print('\b\b\b%s' % msg[i:])

    def add_options(self):
        self.add_opt('-q', '--quick', action='store_true', default=False,
                     help='Print instantly without fancy scrolling effect, saves 2-3 seconds ' +\
                     '(you can also Control-C to make output complete instantly)')

    def run(self):
        self.quick = self.get_opt('quick')
        if self.args:
            self.usage()
        self.print_welcome()


if __name__ == '__main__':
    Welcome().main()
