#!/usr/bin/env python
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-11-28 16:37:00 +0000 (Wed, 28 Nov 2018)
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

Tool to find HDFS file with replication factor 1

These cause problems because taking a single datanode offline may result in alerts for files with missing blocks

Uses any arguments are directory tree paths to starting scanning down. If no argument paths are given, searches under
top level directory /

Uses Hadoop configuration files it expects to find in $HADOOP_HOME/conf to auto-detect
NameNodes HA, Kerberos etc (just kinit first)

Optionally resets such files back to replication factor 3 if specifying --set-replication-factor-3

Tested on Hadoop 2.7 on HDP 2.6 with Kerberos

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
import time
import traceback
import krbV
import snakebite
from snakebite.client import AutoConfigClient
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, log_option, validate_int
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.3'


class HdfsFindReplicationFactor1(CLI):

    def __init__(self):
        # Python 2.x
        super(HdfsFindReplicationFactor1, self).__init__()
        # Python 3.x
        # super().__init__()
        self.path_list = None
        self.replication_factor = None

    def add_options(self):
        super(HdfsFindReplicationFactor1, self).add_options()
        self.add_opt('--hadoop-home',
                     help='Sets $HADOOP_HOME, expects to find config in $HADOOP_HOME/conf, ' + \
                          'otherwise inherits from environment or tries default paths')
        self.add_opt('--set-replication', metavar='N', type=int,
                     help='Resets any files with replication factor 1 back to this replication factor (optional)')

    def process_options(self):
        super(HdfsFindReplicationFactor1, self).process_options()
        self.path_list = self.args
        if not self.path_list:
            self.path_list = ['/']
        self.replication_factor = self.get_opt('set_replication')
        if self.replication_factor is not None:
            validate_int(self.replication_factor, 'set replication', 2, 5)
        hadoop_home = self.get_opt('hadoop_home')
        if hadoop_home is not None:
            os.environ['HADOOP_HOME'] = hadoop_home
        hadoop_home_env = os.getenv('HADOOP_HOME')
        log_option('HADOOP_HOME', hadoop_home_env)
        if hadoop_home_env:
            log.info('will search for Hadoop config in %s/conf', hadoop_home_env)

    def run(self):
        log.info('initiating snakebite hdfs client')
        try:
            client = AutoConfigClient()
        except krbV.Krb5Error as _:  # pylint: disable=no-member
            if self.verbose:
                print('', file=sys.stderr)
            print(_, file=sys.stderr)
        start_time = time.time()
        dir_count = 0
        file_count = 0
        repl1_count = 0
        for path in self.path_list:
            try:
                result_list = client.ls([path], recurse=True, include_toplevel=True, include_children=True)
                for result in result_list:
                    if self.verbose and (dir_count + file_count) % 100 == 0:
                        print('.', file=sys.stderr, end='')
                    if result['block_replication'] == 0:
                        dir_count += 1
                        continue
                    file_count += 1
                    if result['block_replication'] == 1:
                        file_path = result['path']
                        repl1_count += 1
                        if self.verbose:
                            print('', file=sys.stderr)
                        print(file_path)
                        if self.replication_factor:
                            log.info('setting replication factor to %s on %s', self.replication_factor, file_path)
                            # returns a generator so must evaluate in order to actually execute
                            # otherwise you find there is no effect on the replication factor
                            for _ in client.setrep([file_path], self.replication_factor, recurse=False):
                                if 'result' not in _:
                                    print('WARNING: result field not found in setrep result: {}'.format(_),
                                          file=sys.stderr)
                                    continue
                                if not _['result']:
                                    print('WARNING: failed to setrep: {}'.format(_))
            except (snakebite.errors.FileNotFoundException, snakebite.errors.RequestError) as _:
                if self.verbose:
                    print('', file=sys.stderr)
                print(_, file=sys.stderr)
        if self.verbose:
            print('', file=sys.stderr)
        secs = int(time.time() - start_time)
        print('\nCompleted in {} secs\n'.format(secs), file=sys.stderr)
        print('{} files with replication factor 1 out of {} files in {} dirs'\
              .format(repl1_count, file_count, dir_count), file=sys.stderr)


if __name__ == '__main__':
    HdfsFindReplicationFactor1().main()
