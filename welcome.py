#!/usr/bin/env python
#
#  Author: Hari Sekhon
#  Date: 2009-12-09 19:58:14 +0000 (Wed, 09 Dec 2009)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying LICENSE file
#

"""
Prints a slick welcome message with last login time

Tested on Mac OS X and Linux
"""

from __future__ import print_function

__author__  = 'Hari Sekhon'
__version__ = '1.2.0'

import os
import random
import re
import string
import sys
import time
from optparse import OptionParser
libdir = os.path.join(os.path.dirname(__file__), 'pylib')
sys.path.append(libdir)
try:
    from harisekhon.utils import *
    from harisekhon import CLI
except ImportError, e:
    # print('module import failed: %s' % e, file=sys.stderr)
    print >> sys.stderr, 'module import failed: %s' % e
    sys.exit(4)


class Welcome(CLI):

    def construct_msg(self):
        try:
            try:
                user = os.environ['USER'].strip()
                if not user:
                    raise KeyError
            except KeyError:
                user = 'user'
            if not isUser(user):
                print("invalid user '%s' determined from environment variable $USER, failed regex validation" % user)
                sys.exit(ERRORS['CRITICAL'])
            if user == 'root':
                user = user.upper()
            elif len(user) < 4 or re.search('\d', user) or user == 'user':
                # probably not a real name
                pass
            else:
                user = user.title()
            msg = 'Welcome %s - ' % user
            fh = os.popen('last -100')
            fh.readline()
            re_skip = re.compile('^(?:reboot|wtmp)|^\s*$')
            last = ''
            for line in fh:
                last = line.rstrip('\n')
                if(re_skip.match(last)):
                    last = ''
                    continue
                break
            if(last):
                msg += 'last login was '
                last_user = re.sub('\s+.*$', '', last)
                if last_user == 'root':
                    last_user = 'ROOT'
                # strip up to "Day Mon NN" ie "%a %b %e ..."
                (last, num_replacements) = re.subn('.*(\w{3}\s+\w{3}\s+\d+)', '\g<1>', last)
                if(not num_replacements):
                    print('failed to find the date format in the last log')
                    sys.exit(2)
                last = re.sub(' *$', '', last)
                if(last_user == 'ROOT'):
                    msg += 'ROOT'
                elif(last_user.lower() == user.lower()):
                    msg += 'by you'
                else:
                    msg += 'by %s' % last_user
                msg += ' => %s' % last
            else:
                msg += 'no last login information available!'
        except KeyboardInterrupt:
            pass
        return msg


    def print_welcome(self):
        msg = self.construct_msg()
        try:
            charmap = list(string.uppercase + string.lowercase + '@#$%^&*()')
            # print '',
            # print('', end='')
            for i in range(0,len(msg)):
                char = msg[i]
                # print '',
                print(' ', end='')
                j=0
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

    # Don't do this it'll double print since CLI.usage() is now adding usagemsg header
    # def add_options(self):
    #     self.parser = OptionParser(usage=self.usagemsg, version=self.version)

    def run(self):
        if self.args:
            self.usage()
        self.print_welcome()

if __name__ == '__main__':
    Welcome().main()