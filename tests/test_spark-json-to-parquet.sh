#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-05 23:29:15 +0000 (Thu, 05 Nov 2015)
#
#  https://github.com/harisekhon
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

set -eu
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/..";

. tests/travis.sh

cd "$srcdir"

for SPARK_VERSION in 1.3.1 1.4.0; do
    dir="spark-$SPARK_VERSION-bin-hadoop2.6"
    tar="$dir.tgz"
    if ! [ -d "$dir" ]; then
        if ! [ -f "$tar" ]; then
            wget "http://d3kbcqa49mib13.cloudfront.net/$tar"
        fi
        tar zxvf "$tar" || rm -f "$tar" "$dir"
    fi
    echo
    export SPARK_HOME="$dir"
    rm -fr "test-$dir.parquet"
    ../spark-json-to-parquet.py -j test.json -p "test-$dir.parquet" &&
        echo "SUCCEEDED with Spark $SPARK_VERSION" ||
        { echo "FAILED test with Spark $SPARK_VERSION"; exit 1; }
done
echo "SUCCESS"
