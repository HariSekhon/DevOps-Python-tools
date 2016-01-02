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
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

"""

PySpark program to convert JSON file(s) to Parquet

Written to work across Python 2.x and Spark versions, especially Spark given that the Spark API changed after 1.3

"""

from __future__ import print_function

__author__  = 'Hari Sekhon'
__version__ = '0.4.1'

import glob
import logging
import os
import sys
libdir = os.path.join(os.path.dirname(__file__), 'pylib')
sys.path.append(libdir)
try:
    from harisekhon.utils import *
    from harisekhon import CLI
except ImportError as e:
    print('module import failed: %s' % e, file=sys.stderr)
    sys.exit(4)
pyspark_path()
from pyspark import SparkContext
from pyspark import SparkConf
from pyspark.sql import SQLContext

class SparkJsonToParquet(CLI):

    def __init__(self):
        # Python 2.x
        super(SparkJsonToParquet, self).__init__()
        # Python 3.x
        # super().__init__()
        logging.config.fileConfig(os.path.join(libdir, 'resources', 'logging.conf'))
        log = logging.getLogger(self.__class__.__name__)

    # @override
    def add_options(self):
        self.parser.add_option('-j', '--json',       dest='jsonFile',   help='JSON input file/dir ($JSON)',
                               metavar='<file/dir>', default=getenv('JSON'))
        self.parser.add_option('-p', '--parquetDir', dest='parquetDir', help='Parquet output dir ($PARQUETDIR)',
                               metavar='<dir>',      default=getenv('PARQUETDIR'))

    def run(self):
        jsonFile   = self.options.jsonFile
        parquetDir = self.options.parquetDir

        if not jsonFile:
            self.usage('--json not defined')
        if not parquetDir:
            self.usage('--parquetDir not defined')
        if self.args:
            self.usage()

        conf = SparkConf().setAppName('HS PySpark JSON => Parquet')
        sc = SparkContext(conf=conf)
        sqlContext = SQLContext(sc)
        spark_version = sc.version
        log.info('Spark version detected as %s' % spark_version)
        if not isVersionLax(spark_version):
            die("Spark version couldn't be determined. " + support_msg('pytools'))
        if isMinVersion(spark_version, 1.4):
            json = sqlContext.read.json(jsonFile)
            json.write.parquet(parquetDir)
        else:
            log.warn('running legacy code for Spark <= 1.3')
            json = sqlContext.jsonFile(jsonFile)
            json.saveAsParquetFile(parquetDir)

if __name__ == '__main__':
    SparkJsonToParquet().main()
