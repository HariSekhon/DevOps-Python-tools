#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-10 11:47:12 +0100 (Mon, 10 Oct 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

"""

Tool to show distribution of OpenTSDB metrics from import file(s)

Designed to help analyze bulk import files for data skew to help avoid region hotspotting.

One or more files may be given as arguments. Can also read from standard input by specifying a dash as the argument,
similar to standard unix tools.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# from __future__ import unicode_literals

# import logging
import os
import re
# import socket
#import string
import sys
import traceback
# import happybase
import numpy as np
# from thriftpy.thrift import TException as ThriftException
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, log_option, die, code_error, printerr, autoflush, uniq_list_ordered, merge_dicts
    #from harisekhon.utils import validate_host, validate_port, validate_chars
    from harisekhon.utils import validate_file, validate_int
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.3.1'


class OpenTSDBCalculateImportDistribution(CLI):
    def __init__(self):
        # Python 2.x
        super(OpenTSDBCalculateImportDistribution, self).__init__()
        # Python 3.x
        # super().__init__()
        # self.conn = None
        # self.host = None
        # self.port = 9090
        # self.table = None
        self.timeout_default = 3600
        self.files = []
        self.keys = {}
        self.total_keys = 0
        self.re_line = re.compile(r'^\s*(\S+)\s+(\d+)\s+(-?\d+(?:\.\d+)?)\s+(\S+)\s*$')
        self.skip_errors = False
        self.sort_desc = False
        self.prefix_length = None
        self.metric_prefix_header = 'Key Prefix'
        self.metric_prefix_width = len(self.metric_prefix_header)
        self.count_header = 'Count'
        self.count_width = len(self.count_header)
        self.count_pc_header = '% of Total'
        self.count_pc_width = len(self.count_pc_header)
        self.separator = '    '
        self.total_width = (self.metric_prefix_width +
                            self.count_width +
                            self.count_pc_width +
                            len(self.separator) * 2)
        autoflush()

        # def add_options(self):
        # self.add_hostoption(name='HBase Thrift Server', default_host='localhost', default_port=self.port)
        # self.add_opt('-T', '--table', help='Table name')
        self.add_opt('-K', '--key-prefix-length', metavar='<int>', default=self.prefix_length,
                     help='Prefix summary length (default: {0})'.format(self.prefix_length) +
                     '. Use to greater coarser stats')
        # self.add_opt('-l', '--list-tables', action='store_true', help='List tables and exit')
        self.add_opt('--skip-errors', action='store_true', help='Skip lines with errors (exits otherwise)')
        self.add_opt('-d', '--desc', action='store_true', help='Sort descending')

    def process_args(self):
        # log.setLevel(logging.INFO)
        #        self.no_args()
        #        self.host = self.get_opt('host')
        #        self.port = self.get_opt('port')
        #        self.table = self.get_opt('table')
        #        validate_host(self.host)
        #        validate_port(self.port)
        #        if not self.get_opt('list_tables'):
        #            validate_chars(self.table, 'hbase table', 'A-Za-z0-9:._-')
        self.files = self.args
        self.prefix_length = self.get_opt('key_prefix_length')
        self.skip_errors = self.get_opt('skip_errors')
        self.sort_desc = self.get_opt('desc')
        if self.prefix_length is not None:
            validate_int(self.prefix_length, 'key key prefix length', 1, 100)
            self.prefix_length = int(self.prefix_length)
        if not self.files:
            self.usage('no file(s) specified as arguments')
        self.files = uniq_list_ordered(self.files)
        for filename in self.files:
            if filename == '-':
                log_option('file', '<stdin>')
                continue
            validate_file(filename)

            #    def get_tables(self):
            #        try:
            #            return self.conn.tables()
            #        except socket.timeout as _:
            #            die('ERROR while trying to get table list: {0}'.format(_))
            #        except ThriftException as _:
            #            die('ERROR while trying to get table list: {0}'.format(_))

    def run(self):
        # might have to use compat / transport / protocol args for older versions of HBase or if protocol has been
        # configured to be non-default, see:
        # http://happybase.readthedocs.io/en/stable/api.html#connection
        #        try:
        #            log.info('connecting to HBase Thrift Server at %s:%s', self.host, self.port)
        #            self.conn = happybase.Connection(host=self.host, port=self.port, timeout=10 * 1000)  # ms
        #            tables = self.get_tables()
        #            if self.get_opt('list_tables'):
        #                print('Tables:\n\n' + '\n'.join(tables))
        #                sys.exit(3)
        #            if self.table not in tables:
        #                die("HBase table '{0}' does not exist!".format(self.table))
        #            table_conn = self.conn.table(self.table)
        self.populate_metric_counts()
        self.calculate_count_widths()
        self.calculate_key_percentages()
        self.print_key_prefix_counts()
        self.print_summary()
    #            log.info('finished, closing connection')
    #            self.conn.close()
    #        except socket.timeout as _:
    #            die('ERROR: {0}'.format(_))
    #        except ThriftException as _:
    #            die('ERROR: {0}'.format(_))

    def populate_metric_counts(self):
        if self.verbose < 2:
            print('progress dots (1 per new key prefix scanned): ', end='')
        for filename in self.files:
            if filename == '-':
                log.info('reading stdin')
                self.process_file('<stdin>', sys.stdin)
            else:
                log.info("reading file '%s'", filename)
                with open(filename) as file_handle:
                    self.process_file(filename, file_handle)
        if self.verbose < 2:
            print()

    def process_file(self, filename, file_handle):
        for line in file_handle:
            # log.debug(line)
            match = self.re_line.match(line)
            if not match:
                err_msg = "ERROR in file '{0}' on line: {1}".format(filename, line)
                if not self.skip_errors:
                    die(err_msg)
                printerr()
                log.warn(err_msg)
                continue
            metric = match.group(1)
            # don't have a need for this right now
            #timestamp = match.group(2)
            # value = match.grlup(3)
            tags = match.group(4)
            key = metric
            for tag in sorted(tags.split(',')):
                key += ' ' + tag.strip()
            if self.prefix_length is None:
                prefix = key
            else:
                prefix = key[0:min(self.prefix_length, len(key))]
            # prefix = self.bytes_to_str(prefix)
            if not self.keys.get(prefix):
                self.keys[prefix] = {'count': 0}
                if self.verbose < 2:
                    print('.', end='')
            self.keys[prefix]['count'] += 1

    def calculate_count_widths(self):
        for key_prefix in self.keys:
            _ = len(key_prefix)
            if _ > self.metric_prefix_width:
                self.metric_prefix_width = _
            _ = len(str(self.keys[key_prefix]['count']))
            if _ > self.count_width:
                self.count_width = _
            self.total_width = (
                self.metric_prefix_width +
                self.count_width +
                self.count_pc_width +
                len(self.separator) * 2
            )

    def calculate_key_percentages(self):
        log.info('calculating key percentages')
        for key_prefix in self.keys:
            self.total_keys += self.keys[key_prefix]['count']
        # make sure we don't run in to division by zero error
        if self.total_keys == 0:
            die("0 total keys detected!")
        if self.total_keys < 0:
            code_error("negative total keys detected!")
        for key_prefix in self.keys:
            self.keys[key_prefix]['pc'] = '{0:.2f}'.format(self.keys[key_prefix]['count'] /
                                                           max(self.total_keys, 1) * 100)

    def print_key_prefix_counts(self):
        print('=' * self.total_width)
        print('{0:{1}}{2}'.format(self.metric_prefix_header,
                                  self.metric_prefix_width,
                                  self.separator),
              end='')
        print('{0:{1}}{2}{3}'.format(self.count_header,
                                     self.count_width,
                                     self.separator,
                                     self.count_pc_header))
        print('=' * self.total_width)
        tmp_list = [merge_dicts({'key': key}, self.keys[key]) for key in self.keys]
        tmp_list.sort(key=lambda _: _['count'])
        for item in tmp_list:
            print('{0:{1}}{2}'.format(item['key'],
                                      self.metric_prefix_width,
                                      self.separator),
                  end='')
            print('{0:{1}}{2}{3:>10}'.format(item['count'],
                                             self.count_width,
                                             self.separator,
                                             item['pc']))

    def print_summary(self):
        np_keys = np.array([int(self.keys[key]['count']) for key in self.keys])
        avg_keys = np_keys.mean()
        (first_quartile, median, third_quartile) = np.percentile(np_keys, [25, 50, 75]) # pylint: disable=no-member
        print()
        print('Total Keys: {0:d}'.format(self.total_keys))
        if self.prefix_length:
            print('Unique Key Prefixes (length {0}): {1}'.format(self.prefix_length, len(self.keys)))
        else:
            print('Unique Keys: {0}'.format(len(self.keys)))
        print('Average Keys Per Prefix: {0:.2f}'.format(avg_keys))
        print('Average Keys Per Prefix (% of total): {0:.2f}%'.format(avg_keys / self.total_keys * 100))
        width = 0
        for stat in (first_quartile, median, third_quartile):
            _ = len(str(stat))
            if _ > width:
                width = _
        print()
        print('Keys per Prefix:')
        print('1st quartile:  {0:{1}}'.format(first_quartile, width))
        print('median:        {0:{1}}'.format(median, width))
        print('3rd quartile:  {0:{1}}'.format(third_quartile, width))
        print()


if __name__ == '__main__':
    OpenTSDBCalculateImportDistribution().main()
