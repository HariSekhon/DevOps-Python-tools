#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-11-20 12:35:49 +0000 (Sun, 20 Nov 2016)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to abstract and normalize Mac's user/group/host system resolver calls to the same format
as the more standard Linux getent for simplified scripting between the two platforms

Will detect if the platform is Mac and call the necessary commands and translate.

For Linux it becomes a straight pass through to getent.

Supported getent commands: passwd, group

Tested on Linux and Mac OSX 10.10.x (Yosemite)

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

# getent module doesn't parse correctly on Mac:
#
# dict(getent.passwd('root'))
#
# returns 'System Administrator' for shell field

import os
import platform
import re
import subprocess
import sys
import time
import traceback
try:
    import psutil
except ImportError:
    print(traceback.format_exc(), end='')
    sys.exit(4)
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, die, qquit, plural, which, isList, isInt
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'


class Getent(CLI):

    def __init__(self):
        # Python 2.x
        super(Getent, self).__init__()
        # Python 3.x
        # super().__init__()
        # special case to make all following args belong to the passed in command and not to this program
        #self._CLI__parser.disable_interspersed_args()
        self._CLI__parser.set_usage('{prog} [options] <command> <args> ...'.format(prog=self._prog))
        # for Mac to convert to 'x' same as Linux
        self.star_regex = re.compile(r'^\*+$')

    def timeout_handler(self, signum, frame): # pylint: disable=unused-argument
        for child in psutil.Process().children():
            child.kill()
        time.sleep(1)
        qquit('UNKNOWN', 'self timed out after %d second%s' % (self.timeout, plural(self.timeout)))

    def run(self):
        if not self.args:
            self.usage()
        command = self.args[0]
        if len(self.args) > 1:
            args = self.args[1:]
        else:
            args = []
        args_string = ' '.join(self.args[1:])
        operating_system = platform.system()
        if operating_system == 'Darwin':
            log.info('detected system as Mac')
            log.info('calling mac_getent_%s(%s)', command, args_string)
            (formatted_output, returncode) = self.mac_getent(command, args)
            if formatted_output:
                print(formatted_output)
            sys.exit(returncode)
        elif operating_system == 'Linux':
            log.info('detected system as Linux')
            log.info('calling %s %s', command, args_string)
            sys.exit(subprocess.call(['getent', command] + args, shell=False))
        else:
            die("operating system '{operating_system}' is not one of the supported Linux or Darwin (Mac)"\
                .format(operating_system=operating_system))

    def mac_getent(self, command, args):
#        if command == 'passwd':
#            (output, returncode) = self.cmd(command, args)
#            formatted_output = self.mac_getent_passwd(args)
#        elif command == 'group':
#            (output, returncode) = self.cmd(command, args)
#            formatted_output = self.mac_getent_group(output)
#        elif command == 'hosts':
#            (output, returncode) = self.cmd(command, args)
#            formatted_output = self.mac_getent_host(output)
        if command in ('passwd', 'group'): #, 'hosts'):
            # might be too clever to dynamically determine the method to reduce code dup
            (formatted_output, returncode) = getattr(self, 'mac_getent_{command}'.format(command=command))(args)
        else:
            die("unsupported getent command '{0}', must be one of: passwd, group, host".format(command))
        return (formatted_output, returncode)

    def mac_getent_passwd(self, args):
        arg = self.mac_get_arg(args)
        final_returncode = 0
        final_output = ""
        if arg:
            (final_output, final_returncode) = self.mac_getent_passwd_user(arg)
        else:
            users = [user for user in
                     subprocess.Popen('dscl . -list /Users'.split(),
                                      stdout=subprocess.PIPE).stdout.read().split('\n')
                     if user]
            log.info('found users: %s', users)
            for user in users:
                (formatted_output, returncode) = self.mac_getent_passwd_user(user)
                if formatted_output:
                    final_output += formatted_output + '\n'
                if returncode > final_returncode:
                    final_returncode = returncode
            final_output = final_output.rstrip('\n')
            # reorder output by UID to be similar to what you'd see on Linux
            lines = final_output.split('\n')
            final_output = '\n'.join(sorted(lines, cmp=lambda x, y: cmp(int(x.split(':')[2]), int(y.split(':')[2]))))
        return (final_output, final_returncode)

    def mac_getent_passwd_user(self, user):
        log.info('mac_getent_passwd_user(%s)', user)
        command = 'dscl . -read /Users/{user}'.format(user=user)
        (output, returncode) = self.cmd(command)
        user = password = uid = gid = name = homedir = shell = ''
        #log.info('parsing output for passwd conversion')
        output = output.split('\n')
        for (index, line) in enumerate(output):
            tokens = line.split()
            if len(tokens) < 1:
                continue
            field = tokens[0]
            if len(tokens) < 2:
                value = ''
            else:
                value = tokens[1]
            if field == 'RecordName:':
                user = value
            elif field == 'Password:':
                password = value
                if self.star_regex.match(password):
                    password = 'x'
            elif field == 'UniqueID:':
                uid = value
            elif field == 'PrimaryGroupID:':
                gid = value
            elif field == 'RealName:':
                name = value
                if not value and len(output) > index + 1 and output[index+1].startswith(' '):
                    name = output[index+1].strip()
            elif not name and field == 'RecordName:':
                name = value
            elif field == 'NFSHomeDirectory:':
                homedir = value
            elif field == 'UserShell:':
                shell = value
        if not user:
            return('', returncode)
        getent_record = '{user}:{password}:{uid}:{gid}:{name}:{homedir}:{shell}'.format\
                        (user=user, password=password, uid=uid, gid=gid, name=name, homedir=homedir, shell=shell)
        if not isInt(uid, allow_negative=True):
            die("parsing error: UID '{uid}' is not numeric in record {record}!".format(uid=uid, record=getent_record))
        if not isInt(gid, allow_negative=True):
            die("parsing error: GID '{gid}' is not numeric in record {record}!".format(gid=gid, record=getent_record))
        return (getent_record, returncode)

    def mac_getent_group(self, args):
        arg = self.mac_get_arg(args)
        final_returncode = 0
        final_output = ""
        if arg:
            (final_output, final_returncode) = self.mac_getent_group_name(arg)
        else:
            groups = [group for group in
                      subprocess.Popen('dscl . -list /Groups'.split(),
                                       stdout=subprocess.PIPE).stdout.read().split('\n')
                      if group]
            log.info('found groups: %s', groups)
            for group in groups:
                (formatted_output, returncode) = self.mac_getent_group_name(group)
                if formatted_output:
                    final_output += formatted_output + '\n'
                if returncode > final_returncode:
                    final_returncode = returncode
            final_output = final_output.rstrip('\n')
            # reorder output by GID to be similar to what you'd see on Linux
            lines = final_output.split('\n')
            final_output = '\n'.join(sorted(lines, cmp=lambda x, y: cmp(int(x.split(':')[0]), int(y.split(':')[0]))))
        return (final_output, final_returncode)

    def mac_getent_group_name(self, group):
        log.info('mac_getent_group_name(%s)', group)
        command = 'dscl . -read /Groups/{group}'.format(group=group)
        (output, returncode) = self.cmd(command)
        gid = password = name = members = ''
        #log.info('parsing output for group conversion')
        output = output.split('\n')
        for index, line in enumerate(output):
            tokens = line.split()
            if len(tokens) < 1:
                continue
            field = tokens[0]
            if len(tokens) < 2:
                value = ''
            else:
                value = tokens[1]
            if field == 'PrimaryGroupID:':
                gid = value
            elif field == 'Password:':
                password = value
                if self.star_regex.match(password):
                    password = 'x'
            elif field == 'RealName:':
                name = value
                if not value and len(output) > index + 1 and output[index+1].startswith(' '):
                    name = output[index+1].strip()
            elif not name and field == 'RecordName:':
                name = value
            elif field == 'GroupMembership:':
                members = ','.join(tokens[1:])
        if not gid:
            return('', returncode)
        getent_record = '{gid}:{password}:{name}:{members}'.format\
                        (gid=gid, password=password, name=name, members=members)
        if not isInt(gid, allow_negative=True):
            die("parsing error: GID '{gid}' is not numeric in record {record}!".format(gid=gid, record=getent_record))
        return (getent_record, returncode)

#    TODO: dscacheutil is much too slow to be used as a replacement for doing `host <fqdn>`, figure out faster way
#    dscacheutil -q host -a name <fqdn>
#    def mac_getent_host(self, args):
#        arg = self.mac_get_arg(args)
#        (output, returncode) = self.cmd(command)

    @staticmethod
    def mac_get_arg(args):
        if not args:
            return ''
        if not isList(args):
            die("non-list '{args}' passed to mac_getent_passwd()".format(args=args))
        if len(args) > 1:
            die('only one arg is supported on Mac at this time')
        arg = args[0]
        return arg

    @staticmethod
    def cmd(command):
        log.debug('command: %s', command)
        command_binary = command.split()[0]
        if not which(command_binary):
            die("command '{command}' not found in $PATH".format(command=command_binary))
        try:
            process = subprocess.Popen(command.split(),
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
            (stdout, _) = process.communicate()
            process.wait()
            log.debug('returncode: %s', process.returncode)
            log.debug('output: %s\n', stdout)
            return(stdout, process.returncode)
        except subprocess.CalledProcessError as _:
            log.debug('CalledProcessError Exception!')
            log.debug('returncode: %s', _.returncode)
            log.debug('output: %s\n', _.output)
            return(_.output, _.returncode)


if __name__ == '__main__':
    Getent().main()
