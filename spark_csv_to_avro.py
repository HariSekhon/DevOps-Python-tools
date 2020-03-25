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

PySpark program to convert CSV file(s) to Avro

Must either infer schema from header or define schema (column names) on the command line.

If CSV --has-headers then all fields are assumed to be 'string' unless explicitly specified via --schema.

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
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages com.databricks:spark-csv_2.10:1.5.0,' + \
                                    'com.databricks:spark-avro_2.10:2.0.1 %s' \
                                    % os.getenv('PYSPARK_SUBMIT_ARGS', '')
pyspark_path()
from pyspark import SparkContext    # pylint: disable=wrong-import-position,import-error
from pyspark import SparkConf       # pylint: disable=wrong-import-position,import-error
from pyspark.sql import SQLContext  # pylint: disable=wrong-import-position,import-error
from pyspark.sql.types import *     # lgtm [py/polluting-import]  pylint: disable=wrong-import-position,import-error,wildcard-import
from pyspark.sql.types import StructType, StructField  # pylint: disable=wrong-import-position,import-error

__author__ = 'Hari Sekhon'
__version__ = '0.8.1'


class SparkCSVToAvro(CLI):

    def __init__(self):
        # Python 2.x
        super(SparkCSVToAvro, self).__init__()
        # Python 3.x
        # super().__init__()
        # logging.config.fileConfig(os.path.join(libdir, 'resources', 'logging.conf'))
        # log = logging.getLogger(self.__class__.__name__)
        self.verbose_default = 2
        self.timeout_default = 86400
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
        self.add_opt('-c', '--csv', metavar='<file/dir>',
                     help='CSV input file/dir ($CSV)',
                     default=getenv('CSV'))
        self.add_opt('-a', '--avro-dir', metavar='<dir>',
                     help='Avro output dir ($AVRODIR)',
                     default=getenv('AVRODIR'))
        self.add_opt('-e', '--has-header', action='store_true',
                     help='CSV has header. Infers schema if --schema is not given in which case all ' +
                     "types are assumed to be 'string'. Must specify --schema to override this")
        self.add_opt('-s', '--schema', metavar='name:type,name2:type2,...',
                     help="Schema for CSV. Types default to 'string'. Possible types are: %s" \
                     % ', '.join(sorted(self.types_mapping)))

    def parse_args(self):
        self.no_args()
        if not self.get_opt('csv'):
            self.usage('--csv not defined')
        if not self.get_opt('avro_dir'):
            self.usage('--avro-dir not defined')
        if not (self.get_opt('has_header') or self.get_opt('schema')):
            self.usage('must specify either --has-header or --schema')
        # no longer mutually exclusive now this support schema override
        # if self.get_opt('has_header') and self.get_opt('schema'):
        #     self.usage('--has-header and --schema are mutually exclusive')

    def run(self):
        csv_file = self.get_opt('csv')
        avro_dir = self.get_opt('avro_dir')
        has_header = self.get_opt('has_header')
        # I don't know why the Spark guys made this a string instead of a bool
        header_str = 'false'
        if has_header:
            header_str = 'true'
        schema = self.get_opt('schema')
        # let Spark fail if csv/avro dir aren't available
        # can't check paths exist as want to remain generically portable
        # to HDFS, local filesystm or any other uri scheme Spark supports
        log.info("CSV Source: %s" % csv_file)
        log.info("Avro Destination: %s" % avro_dir)

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
                name = str(arg).strip()
                data_type = 'string'
                if ':' in arg:
                    (name, data_type) = arg.split(':', 1)
                data_class = get_type(data_type)
                return StructField(name, data_class, True)
            # see https://github.com/databricks/spark-csv#python-api
            self.schema = StructType([create_struct(_) for _ in schema.split(',')])
            log.info('generated CSV => Spark schema')

        conf = SparkConf().setAppName('HS PySpark CSV => Avro')
        sc = SparkContext(conf=conf) # pylint: disable=invalid-name
        if self.verbose < 3 and 'setLogLevel' in dir(sc):
            sc.setLogLevel('WARN')
        sqlContext = SQLContext(sc)  # pylint: disable=invalid-name
        spark_version = sc.version
        log.info('Spark version detected as %s' % spark_version)

        if not isVersionLax(spark_version):
            die("Spark version couldn't be determined. " + support_msg('pytools'))

        #  pylint: disable=invalid-name
        df = None
        if isMinVersion(spark_version, 1.4):
            if has_header and not schema:
                log.info('inferring schema from CSV headers')
                df = sqlContext.read.format('com.databricks.spark.csv')\
                     .options(header=header_str, inferschema='true')\
                     .load(csv_file)
            else:
                log.info('using explicitly defined schema')
                schema = self.schema
                df = sqlContext.read\
                     .format('com.databricks.spark.csv')\
                     .options(header=header_str)\
                     .load(csv_file, schema=schema)
        else:
            die('Spark <= 1.3 is not supported due to avro dependency, sorry! ' + \
                'I may change this on request but prefer people just upgrade')
            # log.warn('running legacy code for Spark <= 1.3')
            # if has_header and not schema:
            #     log.info('inferring schema from CSV headers')
            #     df = sqlContext.load(source="com.databricks.spark.csv", path=csv_file,
            #                          header=header_str, inferSchema='true')
            # elif self.schema:
            #     log.info('using explicitly defined schema')
            #     df = sqlContext.load(source="com.databricks.spark.csv", path=csv_file,
            #                          header=header_str, schema=self.schema)
            # else:
            #     die('no header and no schema, caught late')
        # this doesn't work in Spark <= 1.3 and the github docs don't mention the older methods for writing avro using
        # the databricks avro driver
        df.write.format('com.databricks.spark.avro').save(avro_dir)

if __name__ == '__main__':
    SparkCSVToAvro().main()
