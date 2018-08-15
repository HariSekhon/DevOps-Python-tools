#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-10 11:47:12 +0100 (Mon, 10 Oct 2016)
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

Tool to show distribution of OpenTSDB metrics from import file(s)

Designed to help analyze bulk import files for data skew to help avoid region hotspotting.

One or more files may be given as arguments. Can also read from standard input by specifying a dash as the argument,
similar to standard unix tools.

Files are expected to be in plaintext opentsdb load format, so if they are compressed with gzip, then decompress
them into a pipe and supply the '-' argument to this program to have them read from standard input:

zcat /path/to/myfiles*.gz | opentsdb_calculate_import_metric_distribution.py -

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# from __future__ import unicode_literals

import os
import re
import sys
import time
import traceback
import numpy as np
libdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'pylib'))
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, log_option, die, code_error, printerr, autoflush, uniq_list_ordered, merge_dicts
    from harisekhon.utils import validate_file, validate_int
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.6'


class OpenTSDBImportDistribution(CLI):
    def __init__(self):
        # Python 2.x
        super(OpenTSDBImportDistribution, self).__init__()
        # Python 3.x
        # super().__init__()
        self.timeout_default = 3600
        self.files = []
        self.keys = {}
        self.total_keys = 0
        self.re_line = re.compile(r'^\s*(\S+)\s+(\d+)\s+(-?\d+(?:\.\d+)?)\s+(\S+=\S+(?:\s+\S+=\S+)*)\s*$')
        self.include_timestamps = False
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

    def add_options(self):
        self.add_opt('-K', '--key-prefix-length', metavar='<int>', default=self.prefix_length,
                     help='Prefix summary length (default: {0})'.format(self.prefix_length) +
                     '. Use to greater coarser stats')
        self.add_opt('-T', '--include-timestamps', action='store_true',
                     help='Include timestamps in the key distribution, summarizing to row hour ' +
                     'as this is how OpenTSDB writes HBase row keys (assumes source is in UTC)')
        self.add_opt('--skip-errors', action='store_true', help='Skip lines with errors (exits otherwise)')
        self.add_opt('-d', '--desc', action='store_true', help='Sort descending')

    def process_args(self):
        self.files = self.args
        self.prefix_length = self.get_opt('key_prefix_length')
        self.skip_errors = self.get_opt('skip_errors')
        self.sort_desc = self.get_opt('desc')
        self.include_timestamps = self.get_opt('include_timestamps')
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

    def run(self):
        self.populate_metric_counts()
        self.calculate_count_widths()
        self.calculate_key_percentages()
        self.print_key_prefix_counts()
        self.print_summary()

    def populate_metric_counts(self):
        if self.verbose < 2:
            print('progress dots (one per 10,000 lines): ', file=sys.stderr, end='')
        for filename in self.files:
            if filename == '-':
                log.info('reading stdin')
                self.process_file('<stdin>', sys.stdin)
            else:
                log.info("reading file '%s'", filename)
                with open(filename) as file_handle:
                    self.process_file(filename, file_handle)
        if self.verbose < 2:
            print(file=sys.stderr)

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
            timestamp = match.group(2)
            # don't have a need for this right now
            # value = match.group(3)
            tags = match.group(4)
            key = metric
            if self.include_timestamps:
                timestamp = int(timestamp)
                # remove millis
                if len(str(timestamp)) >= 15:
                    timestamp = round(timestamp / 1000)
                hour = time.strftime('%Y-%m-%d %H:00', time.gmtime(timestamp))
                key += ' ' + hour
            for tag in sorted(tags.split()):
                key += ' ' + tag.strip()
            if self.prefix_length is None:
                prefix = key
            else:
                prefix = key[0:min(self.prefix_length, len(key))]
            # prefix = self.bytes_to_str(prefix)
            if not self.keys.get(prefix):
                self.keys[prefix] = {'count': 0}
            self.keys[prefix]['count'] += 1
            self.total_keys += 1
            if self.verbose < 2 and self.total_keys % 10000 == 0:
                print('.', file=sys.stderr, end='')

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
        # incremented instead now for one progress dot per 10k lines
        #for key_prefix in self.keys:
        #    self.total_keys += self.keys[key_prefix]['count']
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
        print('Average Keys Per Prefix: {0:.2f} ({1:.2f}%)'.format(avg_keys, avg_keys / self.total_keys * 100))
        width = 0
        for stat in (first_quartile, median, third_quartile):
            _ = len(str(stat))
            if _ > width:
                width = _
        print()
        print('Keys per Prefix:')
        print('1st quartile:  {0:{1}} ({2:.2f}%)'.format(first_quartile, width, first_quartile / self.total_keys * 100))
        print('median:        {0:{1}} ({2:.2f}%)'.format(median, width, median / self.total_keys * 100))
        print('3rd quartile:  {0:{1}} ({2:.2f}%)'.format(third_quartile, width, third_quartile / self.total_keys * 100))
        print()


if __name__ == '__main__':
    OpenTSDBImportDistribution().main()
