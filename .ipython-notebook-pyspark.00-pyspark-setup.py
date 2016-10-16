#
#  Author: Hari Sekhon
#  Date: 22/8/2014
#

# Yarn library support

# Requires SPARK_HOME to be set

__author__  = "Hari Sekhon"
__version__ = "0.1"

import glob
import os
import sys

# This only runs PySpark in local mode, not Yarn mode
#
# See ipython-notebook-spark.py for cluster mode (YARN or Standalone)

spark_home = os.getenv('SPARK_HOME', None)
if not spark_home:
    raise ValueError('SPARK_HOME environment variable is not set')
sys.path.insert(0, os.path.join(spark_home, 'python'))
for lib in glob.glob(os.path.join(spark_home, 'python/lib/py4j-*-src.zip')):
    sys.path.insert(0, lib)
execfile(os.path.join(spark_home, 'python/pyspark/shell.py'))
