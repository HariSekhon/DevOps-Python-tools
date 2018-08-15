#!/usr/bin/env python
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-03 21:38:52 +0000 (Tue, 03 Nov 2015)
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

PySpark program to convert Avro file(s) to Parquet

Written to work across Python 2.x, supports Spark 1.4+

Tested on Spark 1.4.0, 1.5.1, 1.6.0, 1.6.2, 2.0.0 (requires spark-avro package 3.0.0+)

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
# from __future__ import unicode_literals

import os
import sys
libdir = os.path.join(os.path.dirname(__file__), 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log, isMinVersion, support_msg, isVersionLax, die, getenv, pyspark_path
    from harisekhon import CLI
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    print("Did you remember to build the project by running 'make'?", file=sys.stderr)
    print("Alternatively perhaps you tried to copy this program out without it's adjacent libraries?", file=sys.stderr)
    sys.exit(4)
                                    # com.databricks:spark-avro_2.10:2.0.1 - 2.0.1 is for Spark 1.4+
                                    # you can edit this bit if you need to run it on Spark 1.3:
                                    # https://github.com/databricks/spark-avro#linking
# Must set spark-avro package to 3.0.0+ if using Spark 2.0
# for Spark < 2.0 it results in Exception:
# Caused by: java.lang.ClassNotFoundException: org.apache.spark.sql.execution.datasources.FileFormat
#os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages com.databricks:spark-avro_2.10:3.0.0 %s' \
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages com.databricks:spark-avro_2.10:2.0.1 %s' \
                                    % os.getenv('PYSPARK_SUBMIT_ARGS', '')
pyspark_path()
from pyspark import SparkContext    # pylint: disable=wrong-import-position,import-error
from pyspark import SparkConf       # pylint: disable=wrong-import-position,import-error
from pyspark.sql import SQLContext  # pylint: disable=wrong-import-position,import-error

__author__ = 'Hari Sekhon'
__version__ = '0.8.0'


class SparkAvroToParquet(CLI):

    def __init__(self):
        # Python 2.x
        super(SparkAvroToParquet, self).__init__()
        # Python 3.x
        # super().__init__()
        # logging.config.fileConfig(os.path.join(libdir, 'resources', 'logging.conf'))
        # log = logging.getLogger(self.__class__.__name__)
        self.verbose_default = 2
        self.timeout_default = 86400

    # @override
    def add_options(self):
        self.add_opt('-a', '--avro', metavar='<file/dir>',
                     help='Avro input file/dir ($AVRO)',
                     default=getenv('AVRO'))
        self.add_opt('-p', '--parquet-dir', metavar='<dir>',
                     help='Parquet output dir ($PARQUETDIR)',
                     default=getenv('PARQUETDIR'))

    def parse_args(self):
        self.no_args()
        if not self.get_opt('avro'):
            self.usage('--avro not defined')
        if not self.get_opt('parquet_dir'):
            self.usage('--parquet-dir not defined')

    def run(self):
        avro_file = self.get_opt('avro')
        parquet_dir = self.get_opt('parquet_dir')
        # let Spark fail if avro/parquet aren't available
        # can't check paths exist as want to remain generically portable
        # to HDFS, local filesystm or any other uri scheme Spark supports
        log.info("Avro Source: %s" % avro_file)
        log.info("Parquet Destination: %s" % parquet_dir)

        conf = SparkConf().setAppName('HS PySpark Avro => Parquet')
        sc = SparkContext(conf=conf) # pylint: disable=invalid-name
        if self.verbose < 3 and 'setLogLevel' in dir(sc):
            sc.setLogLevel('WARN')
        sqlContext = SQLContext(sc)  # pylint: disable=invalid-name
        spark_version = sc.version
        log.info('Spark version detected as %s' % spark_version)

        if not isVersionLax(spark_version):
            die("Spark version couldn't be determined. " + support_msg('pytools'))

        #  pylint: disable=invalid-name
        if isMinVersion(spark_version, 1.4):
            # this doesn't work in Spark <= 1.3 - github docs don't mention the older .method() for reading avro
            df = sqlContext.read.format('com.databricks.spark.avro').load(avro_file)
            df.write.parquet(parquet_dir)
        else:
            die('Spark <= 1.3 is not supported due to avro dependency, sorry! ' + \
                'I may change this on request but prefer people just upgrade')
            # log.warn('running legacy code for Spark <= 1.3')
            # df.saveAsParquetFile(parquet_dir)


if __name__ == '__main__':
    SparkAvroToParquet().main()
