#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-05 23:29:15 +0000 (Thu, 05 Nov 2015)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

set -eu
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "
# ===================== #
# Spark CSV => Parquet
# ===================== #
"

cd "$srcdir/..";

. ./tests/utils.sh

cd "$srcdir"

for SPARK_VERSION in 1.3.1 1.4.0; do
    dir="spark-$SPARK_VERSION-bin-hadoop2.6"
    tar="$dir.tgz"
    if ! [ -d "$dir" ]; then
        if ! [ -f "$tar" ]; then
            echo "fetching $tar"
            # some systems don't have wget
            if which wget &>/dev/null; then
                wget "http://d3kbcqa49mib13.cloudfront.net/$tar"
            else
                curl -L "http://d3kbcqa49mib13.cloudfront.net/$tar" > "$tar"
            fi
        fi
        echo "untarring $tar"
        tar zxf "$tar" || rm -f "$tar" "$dir"
    fi
    echo
    export SPARK_HOME="$dir"
    rm -fr "test-$dir.parquet"
    # this works for both Spark 1.3.1 and 1.4.0 but calling from within spark-csv-to-parquet.py doesn't like it
    #spark-submit --packages com.databricks:spark-csv_2.10:1.3.0 ../spark-csv-to-parquet.py -c data/test.csv -p "test-$dir.parquet" --has-header $@ &&
    # resolved, was due to Spark 1.4+ requiring pyspark-shell for PYSPARK_SUBMIT_ARGS
    ../spark-csv-to-parquet.py -c data/test.csv -p "test-$dir.parquet" --has-header $@ &&
        echo "SUCCEEDED with Spark $SPARK_VERSION" ||
        { echo "FAILED test with Spark $SPARK_VERSION"; exit 1; }
done
echo "SUCCESS"
