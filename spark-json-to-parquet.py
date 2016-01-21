#!/usr/bin/env python
#  pylint: disable=invalid-name
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-03 21:38:52 +0000 (Tue, 03 Nov 2015)
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

PySpark program to convert JSON file(s) to Parquet

Written to work across Python 2.x and Spark versions, especially Spark given that the Spark API changed after 1.3

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys
libdir = os.path.join(os.path.dirname(__file__), 'pylib')
sys.path.append(libdir)
try:
    from harisekhon.utils import log, isMinVersion, support_msg, isVersionLax, die, getenv, pyspark_path # pylint: disable=wrong-import-position
    from harisekhon import CLI # pylint: disable=wrong-import-position
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    sys.exit(4)
pyspark_path()
from pyspark import SparkContext    # pylint: disable=wrong-import-position,import-error
from pyspark import SparkConf       # pylint: disable=wrong-import-position,import-error
from pyspark.sql import SQLContext  # pylint: disable=wrong-import-position,import-error

__author__ = 'Hari Sekhon'
__version__ = '0.6.0'

class SparkJsonToParquet(CLI):

    # def __init__(self):
        # Python 2.x
        # super(SparkJsonToParquet, self).__init__()
        # Python 3.x
        # super().__init__()
        # logging.config.fileConfig(os.path.join(libdir, 'resources', 'logging.conf'))
        # log = logging.getLogger(self.__class__.__name__)

    # @override
    def add_options(self):
        self.set_verbose_default(2)
        self.set_timeout_default(86400)
        self.parser.add_option('-j', '--json', metavar='<file/dir>',
                               help='JSON input file/dir ($JSON)',
                               default=getenv('JSON'))
        self.parser.add_option('-p', '--parquet-dir', metavar='<dir>',
                               help='Parquet output dir ($PARQUETDIR)',
                               default=getenv('PARQUETDIR'))

    def parse_args(self):
        self.no_args()
        if not self.options.json:
            self.usage('--json not defined')
        if not self.options.parquet_dir:
            self.usage('--parquet-dir not defined')

    def run(self):
        json_file = self.options.json
        parquet_dir = self.options.parquet_dir
        # let Spark fail if csv/parquet aren't available
        # can't check paths exist as want to remain generically portable
        # to HDFS, local filesystm or any other uri scheme Spark supports
        log.info("Json Source: %s" % json_file)
        log.info("Parquet Destination: %s" % parquet_dir)

        conf = SparkConf().setAppName('HS PySpark JSON => Parquet')
        sc = SparkContext(conf=conf) # pylint: disable=invalid-name
        sqlContext = SQLContext(sc)  # pylint: disable=invalid-name
        spark_version = sc.version
        log.info('Spark version detected as %s' % spark_version)
        if not isVersionLax(spark_version):
            die("Spark version couldn't be determined. " + support_msg('pytools'))
        if isMinVersion(spark_version, 1.4):
            df = sqlContext.read.json(json_file)
            df.write.parquet(parquet_dir)
        else:
            log.warn('running legacy code for Spark <= 1.3')
            df = sqlContext.jsonFile(json_file)
            df.saveAsParquetFile(parquet_dir)

if __name__ == '__main__':
    SparkJsonToParquet().main()
