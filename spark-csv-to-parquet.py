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

PySpark program to convert CSV file(s) to Parquet

Must either infer schema from header or define schema (column names) on the command line.

If CSV --has-headers then all fields are assumed to be 'string' unless explicitly specified via --schema.

Written to work across Python 2.x and Spark versions, especially Spark given that the Spark API changed after 1.3

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
    from harisekhon.utils import log, isMinVersion, support_msg, isVersionLax, die, getenv, pyspark_path # pylint: disable=wrong-import-position
    from harisekhon import CLI # pylint: disable=wrong-import-position
except ImportError as _:
    print('module import failed: %s' % _, file=sys.stderr)
    sys.exit(4)
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages com.databricks:spark-csv_2.10:1.3.0 %s' \
                                    % os.getenv('PYSPARK_SUBMIT_ARGS', '')
pyspark_path()
from pyspark import SparkContext    # pylint: disable=wrong-import-position,import-error
from pyspark import SparkConf       # pylint: disable=wrong-import-position,import-error
from pyspark.sql import SQLContext  # pylint: disable=wrong-import-position,import-error
from pyspark.sql.types import *     # pylint: disable=wrong-import-position,import-error,wildcard-import
from pyspark.sql.types import StructType, StructField  # pylint: disable=wrong-import-position,import-error

__author__ = 'Hari Sekhon'
__version__ = '0.7.0'

class SparkCSVToParquet(CLI):

    def __init__(self):
        # Python 2.x
        super(SparkCSVToParquet, self).__init__()
        # Python 3.x
        # super().__init__()
        # logging.config.fileConfig(os.path.join(libdir, 'resources', 'logging.conf'))
        # log = logging.getLogger(self.__class__.__name__)
        self.schema = None
        self.types_mapping = {}
        # dynamically generate types mapping from available types in PySpark
        from pyspark.sql import types # pylint: disable=wrong-import-position,import-error
        for _ in dir(types):
            if _.endswith('Type'):
                self.types_mapping[_[:-4].lower()] = _
        if 'integer' in self.types_mapping:
            # because I like typing int better than integer
            self.types_mapping['int'] = self.types_mapping['integer']

    # @override
    def add_options(self):
        self.set_verbose_default(2)
        self.set_timeout_default(86400)
        self.parser.add_option('-c', '--csv', metavar='<file/dir>',
                               help='CSV input file/dir ($CSV)',
                               default=getenv('CSV'))
        self.parser.add_option('-p', '--parquet-dir', metavar='<dir>',
                               help='Parquet output dir ($PARQUETDIR)',
                               default=getenv('PARQUETDIR'))
        self.parser.add_option('-e', '--has-header', action='store_true',
                               help='CSV has header (infers schema if --schema is not given in which case all ' +
                               "types are assumed to be 'string'. Must specify --schema to override this")
        self.parser.add_option('-s', '--schema',
                               help="Schema for CSV. Format is '<name>:<type>,<name2>:<type>...' where type " +
                               "defaults to 'string', possible types are: %s" % ''.join(sorted(self.types_mapping)))

    def parse_args(self):
        self.no_args()
        if not self.options.csv:
            self.usage('--csv not defined')
        if not self.options.parquet_dir:
            self.usage('--parquet_dir not defined')
        if not (self.options.has_header or self.options.schema):
            self.usage('must specify either --has-header or --schema')
        # no longer mutually exclusive now this support schema override
        # if self.options.has_header and self.options.schema:
        #     self.usage('--has-header and --schema are mutually exclusive')

    def run(self):
        csv_file = self.options.csv
        parquet_dir = self.options.parquet_dir
        has_header = self.options.has_header
        # I don't know why the Spark guys made this a string instead of a bool
        header_str = 'false'
        if has_header:
            header_str = 'true'
        schema = self.options.schema
        # let Spark fail if csv/parquet aren't available
        # can't check paths exist as want to remain generically portable
        # to HDFS, local filesystm or any other uri scheme Spark supports
        log.info("CSV Source: %s" % csv_file)
        log.info("Parquet Destination: %s" % parquet_dir)

        if schema:
            def get_type(arg):
                arg = str(arg).lower()
                if arg not in self.types_mapping:
                    self.usage("invalid type '%s' defined in --schema, must be one of: %s"
                               % (arg, ', '.join(sorted(self.types_mapping.keys()))))
                # return self.types_mapping[arg]
                module = __import__('pyspark.sql.types', globals(), locals(), ['types'], -1)
                class_ = getattr(module, self.types_mapping[arg])
                _ = class_()
                return _

            def create_struct(arg):
                name = arg
                data_type = 'string'
                if ':' in arg:
                    (name, data_type) = arg.split(':', 1)
                data_class = get_type(data_type)
                return StructField(name, data_class, True)
            # see https://github.com/databricks/spark-csv#python-api
            self.schema = StructType([create_struct(_) for _ in schema.split(',')])
            log.info('generated schema')

        conf = SparkConf().setAppName('HS PySpark CSV => Parquet')
        sc = SparkContext(conf=conf) # pylint: disable=invalid-name
        sqlContext = SQLContext(sc)  # pylint: disable=invalid-name
        spark_version = sc.version
        log.info('Spark version detected as %s' % spark_version)

        if not isVersionLax(spark_version):
            die("Spark version couldn't be determined. " + support_msg('pytools'))

        df = None
        if isMinVersion(spark_version, 1.4):
            if has_header and not schema:
                log.info('inferring schema from CSV headers')
                df = sqlContext.read.format('com.databricks.spark.csv')\
                     .options(header=header_str, inferschema='true')\
                     .load(csv_file)
            else:
                log.info('using explicitly defined schema')
                df = sqlContext.read\
                     .format('com.databricks.spark.csv')\
                     .options(header=header_str)\
                     .load(csv_file, schema=self.schema)
            df.write.parquet(parquet_dir)
        else:
            log.warn('running legacy code for Spark <= 1.3')
            if has_header and not schema:
                log.info('inferring schema from CSV headers')
                df = sqlContext.load(source="com.databricks.spark.csv", path=csv_file,
                                     header=header_str, inferSchema='true')
            elif self.schema:
                log.info('using explicitly defined schema')
                df = sqlContext.load(source="com.databricks.spark.csv", path=csv_file,
                                     header=header_str, schema=self.schema)
            else:
                die('no header and no schema, caught late')
            df.saveAsParquetFile(parquet_dir)

if __name__ == '__main__':
    SparkCSVToParquet().main()
