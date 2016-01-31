#!/usr/bin/env python
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

PySpark program to convert to Parquet file(s) to Avro

Written to work across Python 2.x, supports Spark 1.4+

Tested on Spark 1.4.0, 1.6.0

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
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages com.databricks:spark-avro_2.10:2.0.1 %s' \
                                    % os.getenv('PYSPARK_SUBMIT_ARGS', '')
pyspark_path()
from pyspark import SparkContext    # pylint: disable=wrong-import-position,import-error
from pyspark import SparkConf       # pylint: disable=wrong-import-position,import-error
from pyspark.sql import SQLContext  # pylint: disable=wrong-import-position,import-error

__author__ = 'Hari Sekhon'
__version__ = '0.7.0'

class SparkParquetToAvro(CLI):

    def __init__(self):
        # Python 2.x
        super(SparkParquetToAvro, self).__init__()
        # Python 3.x
        # super().__init__()
        # logging.config.fileConfig(os.path.join(libdir, 'resources', 'logging.conf'))
        # log = logging.getLogger(self.__class__.__name__)

    # @override
    def add_options(self):
        self.set_verbose_default(2)
        self.set_timeout_default(86400)
        self.parser.add_option('-p', '--parquet', metavar='<file/dir>',
                               help='Parquet input file/dir ($PARQUET)',
                               default=getenv('PARQUET'))
        self.parser.add_option('-a', '--avro-dir', metavar='<dir>',
                               help='Avro output dir ($AVRODIR)',
                               default=getenv('AVRODIR'))

    def parse_args(self):
        self.no_args()
        if not self.options.parquet:
            self.usage('--parquet not defined')
        if not self.options.avro_dir:
            self.usage('--avro-dir not defined')

    def run(self):
        parquet_file = self.options.parquet
        avro_dir = self.options.avro_dir
        # let Spark fail if avro/parquet aren't available
        # can't check paths exist as want to remain generically portable
        # to HDFS, local filesystm or any other uri scheme Spark supports
        log.info("Parquet Source: %s" % parquet_file)
        log.info("Avro Destination: %s" % avro_dir)

        conf = SparkConf().setAppName('HS PySpark Parquet => Avro')
        sc = SparkContext(conf=conf) # pylint: disable=invalid-name
        sqlContext = SQLContext(sc)  # pylint: disable=invalid-name
        spark_version = sc.version
        log.info('Spark version detected as %s' % spark_version)

        if not isVersionLax(spark_version):
            die("Spark version couldn't be determined. " + support_msg('pytools'))

        #  pylint: disable=invalid-name
        if isMinVersion(spark_version, 1.4):
            # this doesn't work in Spark <= 1.3 - github docs don't mention the older .method() for writing avro
            df = sqlContext.read.parquet(parquet_file)
            df.write.format('com.databricks.spark.avro').save(avro_dir)
        else:
            die('Spark <= 1.3 is not supported due to avro dependency, sorry! ' + \
                'I may change this on request but prefer people just upgrade')
            # log.warn('running legacy code for Spark <= 1.3')
            # df.saveAsParquetFile(parquet_dir)

if __name__ == '__main__':
    SparkParquetToAvro().main()
