#!/usr/bin/env python
#
#  Author: Hari Sekhon
#  Date: 2009-12-09 19:58:14 +0000 (Wed, 09 Dec 2009)
#
#  http://github.com/harisekhon/pytools
#
#  License: see accompanying LICENSE file
#

"""

Prints a slick welcome message with last login time

Tested on Mac OS X and Linux

"""

__author__  = "Hari Sekhon"
__version__ = "1.0"

import os
import random
import re
import string
import sys
import time

if(len(sys.argv) > 1):
    print >> sys.stderr, "usage: welcome.py"
    sys.exit(3)

try:
    try:
        user = os.environ['USER'].strip()
        if not user:
            raise KeyError
    except KeyError:
        user = "user"
    if not re.match('^[A-Za-z][A-Za-z0-9-]*[A-Za-z0-9]$', user):
        print "invalid user '%s' determined from environment variable $USER, failed regex validation" % user
        sys.exit(1)
    if user == "root":
        user = user.upper()
    elif len(user) < 4 or re.search('\d', user) or user == "user":
        # probably not a real name
        pass
    else:
        user = user.title()
    msg = "Welcome %s - " % user
    fh = os.popen("last -100")
    fh.readline()
    re_skip = re.compile('^(?:reboot|wtmp)|^\s*$')
    last = ""
    for line in fh:
        last = line.rstrip("\n")
        if(re_skip.match(last)):
            last = ""
            continue
        break
    if(last):
        msg += "last login was "
        last_user = re.sub('\s+.*$', '', last)
        if last_user == "root":
            last_user = "ROOT"
        # strip up to "Day Mon NN" ie "%a %b %e ..."
        (last, num_replacements) = re.subn('.*(\w{3}\s+\w{3}\s+\d+)', '\g<1>', last)
        if(not num_replacements):
            print "failed to find the date format in the last log";
            sys.exit(2)
        last = re.sub(' *$', '', last)
        if(last_user == "ROOT"):
            msg += "ROOT"
        elif(last_user.lower() == user.lower()):
            msg += "by you"
        else:
            msg += "by %s" % last_user
        msg += " => %s" % last
    else:
        msg += "no last login information available!"
except KeyboardInterrupt:
    pass

try:
    charmap = list(string.uppercase + string.lowercase + "@#$%^&*()")

    print "",
    for i in range(0,len(msg)):
        char = msg[i]
        print "",
        j=0
        while 1:
            if j > 3:
                random_char = char
            else:
                random_char = random.choice(charmap)
            print '\b\b%s' % random_char,
            sys.stdout.flush()
            #print '%s' % random_char,
            if char == random_char:
                break
            j += 1
            time.sleep(0.0085)
except KeyboardInterrupt:
    print "\b\b\b\b%s" % msg[i:]
