#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-16 15:44:16 +0000 (Sat, 16 Jan 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#  to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

"""

Serf Handler to return query information or handle specific events

For user queries checks first arg against $PATH and if matching executable is found, executes and returns the result
from standard output of the full command. Careful to ensure you've set up security before using this!

https://www.serfdom.io/intro/getting-started/event-handlers.html

https://www.serfdom.io/docs/commands/event.html

Tested on HashiCorp's Serf 0.7.0

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import logging
import os
import re
import sys
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    from harisekhon.utils import log, which, FileNotFoundException # pylint: disable=wrong-import-position
    from harisekhon import CLI # pylint: disable=wrong-import-position
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'

class SerfEventHandler(CLI):

    def __init__(self):
        super(SerfEventHandler, self).__init__()
        self.events = ['member-join', 'member-leave', 'member-failed', 'member-update', 'member-reap', 'user', 'query']
        self.event = None
        self.set_timeout_default(None)

    # override this if subclassing
    def handle_event(self):
        if self.event == 'query':
            query_name = os.getenv('SERF_QUERY_NAME')
            # if the query is found in the path then execute the command
            try:
                if which(query_name.split()[0]):
                    print(os.popen(query_name).read(), end='')
            except FileNotFoundException as _:
                print(_)
        for line in sys.stdin:
            # do something with the data
            log.debug('data: %s' % line.strip())

    def run(self):
        if self.args:
            self.usage()
        if log.isEnabledFor(logging.DEBUG):
            # this trips the 1024 byte limit and queries fail to respond
            # log.debug(envs2str())
            serf_regex = re.compile('SERF', re.I)
            for (key, value) in os.environ.iteritems(): # pylint: disable=unused-variable
                if serf_regex.search(key):
                    log.debug('%(key)s=%(value)s' % locals())
        self.event = os.getenv('SERF_EVENT', None)
        if self.event is None:
            log.warn('SERF_EVENT environment variable was None!!')
        elif self.event not in self.events:
            log.warn("SERF_EVENT environment variable passed unrecognized event type '%s'" % self.event)
        self.handle_event()


if __name__ == '__main__':
    SerfEventHandler().main()
