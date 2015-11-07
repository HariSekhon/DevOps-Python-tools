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

"""

from __future__ import print_function

__author__  = 'Hari Sekhon'
__version__ = '0.3.1'

try:
    import glob
    import os
    import sys
    # using optparse rather than argparse for servers still on Python 2.6
    from optparse import OptionParser
    sys.path.append(os.path.dirname(os.path.abspath(sys.argv[0])) + '/lib')
    from HariSekhonUtils import *
    spark_home = os.getenv('SPARK_HOME', None)
    if spark_home:
        # doesn't contain py4j may as well just use the already unpacked version
        #sys.path.append(os.path.join(spark_home, 'python/lib/pyspark.zip'))
        sys.path.append(os.path.join(spark_home, 'python'))
        # more abstract without version number but not available in spark bin download
        #sys.path.append(os.path.join(spark_home, 'python/build'))
        for x in glob.glob(os.path.join(spark_home, 'python/lib/py4j-*-src.zip')):
            sys.path.append(x)
    else:
        warn("SPARK_HOME not set - probably won't find PySpark libs")
    from pyspark import SparkContext
    from pyspark import SparkConf
    from pyspark.sql import SQLContext
except ImportError, e:
    print('module import failed: %s' % e)
    sys.exit(3)
except Exception, e:
    print('exception encountered during module import: %s' % e)
    sys.exit(3)

def main():
    # bit hackish and hard to keep aligned with docstring changes, not using this
    # usage = '\r\b\r\b\r' + __doc__ + "usage: %prog -j file.json -p directory.parquet"
    # parser = OptionParser(usage=usage, version='%prog ' + __version__)
    parser = OptionParser(version='%prog ' + __version__)
    parser.add_option('-j', '--json', dest='jsonFile', help='JSON input file/dir', metavar='<file/dir>')
    parser.add_option('-p', '--parquetDir', dest='parquetDir', help='Parquet output dir', metavar='<dir>')

    (options, args) = parser.parse_args()

    jsonFile   = options.jsonFile
    parquetDir = options.parquetDir

    if args or not jsonFile or not parquetDir:
        parser.print_help()
        sys.exit(ERRORS['UNKNOWN'])

    conf = SparkConf().setAppName('HS PySpark JSON => Parquet')
    sc = SparkContext(conf=conf)
    sqlContext = SQLContext(sc)
    spark_version = sc.version
    print('Spark version detected as %s' % spark_version)
    if not isVersionLax(spark_version):
        die("Spark version couldn't be determined. " + support_msg('pytools'))
    if isMinVersion(spark_version, 1.4):
        json = sqlContext.read.json(jsonFile)
        json.write.parquet(parquetDir)
    else:
        print('running legacy code for Spark <= 1.3')
        json = sqlContext.jsonFile(jsonFile)
        json.saveAsParquetFile(parquetDir)

if __name__ == '__main__':
    main()