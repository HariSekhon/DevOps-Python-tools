#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-16 15:44:16 +0000 (Sat, 16 Jan 2016)
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

Serf Handler to return query information or handle specific events

Optionally allows enabling command pass through of any user query or event

Checks first arg against $PATH and if matching executable is found, then executes the full command and returns the
result from standard output. Careful to ensure you've set up security before enabling --cmd!

Framework for new custom handlers, simply inherit SerfEventHandler and override add_options() and handle_event() methods

Docs:

https://www.serfdom.io/intro/getting-started/event-handlers.html

https://www.serfdom.io/docs/agent/event-handlers.html

Call custom events:

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
    # pylint: disable=wrong-import-position
    from harisekhon.utils import isStr, log, which
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.2.2'

class SerfEventHandler(CLI):

    def __init__(self):
        super(SerfEventHandler, self).__init__()
        # allow shorter default 10 sec timeout
        # self.timeout_default = 30
        self.events = ['member-join', 'member-leave', 'member-failed', 'member-update', 'member-reap', 'user', 'query']
        self.node = os.getenv('SERF_SELF_NAME', '')
        self.role = os.getenv('SERF_SELF_ROLE', None)
        self.event = os.getenv('SERF_EVENT', None)
        self.query_name = os.getenv('SERF_QUERY_NAME', None)
        self.user_event = os.getenv('SERF_USER_EVENT', None)
        # self.user_ltime = os.getenv('SERF_USER_LTIME', 0)
        # self.query_ltime = os.getenv('SERF_QUERY_LTIME', 0)
        self.command = None
        # "expected to exit within a reasonable amount of time" according to docs, this seems like a reasonable
        # safeguard and is configurable on the command line via --timeout <secs>
        if self.event is None:
            log.warn('SERF_EVENT environment variable was None!!')
        elif self.event not in self.events:
            log.warn("SERF_EVENT environment variable passed unrecognized event type '%s'" % self.event)

    def add_option_command_passthru(self):
        self.add_opt('--cmd-passthru', dest='cmd', action='store_true',
                     help='Allow any query or event to run a command if the first arg is found in $PATH')

    # this allows easier overriding of add_options while adding command passthrough option back in
    def add_options(self):
        self.add_option_command_passthru()

    def enable_commands(self):
        if self.event in ['query', 'event']:
            cmd = None
            if self.event == 'query':
                cmd = self.query_name
            elif self.event == 'user':
                cmd = self.user_event
            # if the first part of the query is found in $PATH then assume it's a command that was passed
            if which(cmd.split()[0]):
                self.command = cmd

    # override this if subclassing
    def handle_event(self):
        if isStr(self.command):
            print(os.popen(self.command).read(), end='')
        for line in sys.stdin:
            # do something with the data
            log.debug('data: %s' % line.strip())

    def run(self):
        if self.args:
            self.usage()
        if log.isEnabledFor(logging.DEBUG):
            # this trips the 1024 byte limit and queries fail to respond so only filter and show *SERF* env vars
            # log.debug(envs2str())
            serf_regex = re.compile('SERF', re.I)
            for (key, value) in os.environ.iteritems(): # pylint: disable=unused-variable
                if serf_regex.search(key):
                    log.debug('%(key)s=%(value)s' % locals())
        if 'cmd' in dir(self.options) and self.get_opt('cmd'):
            self.enable_commands()
        self.handle_event()


if __name__ == '__main__':
    SerfEventHandler().main()
