#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-05 23:29:15 +0000 (Thu, 05 Nov 2015)
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -eu
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir"

# shellcheck disable=SC1091
. ./utils.sh

section "Spark JSON => Avro"

if is_inside_docker; then
    echo "detected running inside docker, skipping test..."
    return 0 &>/dev/null || :
    exit 0
fi

# don't support Spark <= 1.3 due to difference in databricks avro dependency
export SPARK_VERSIONS="${*:-1.4.0 1.5.1 1.6.2}"
# requires upgrade to spark-avro 3.0.0
#export SPARK_VERSIONS="${*:-2.0.0}"

for SPARK_VERSION in $SPARK_VERSIONS; do
    dir="spark-$SPARK_VERSION-bin-hadoop2.6"
    tar="$dir.tgz"
    if ! [ -d "$dir" ]; then
        if ! [ -f "$tar" ]; then
            echo "fetching $tar"
            # some systems don't have wget
            if type -P wget &>/dev/null; then
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
    # this works for both Spark 1.3.1 and 1.4.0 but calling from within spark-csv-to-avro.py doesn't like it
    #spark-submit --packages com.databricks:spark-csv_2.10:1.3.0 ../spark-csv-to-avro.py -c data/test.csv -a "test-$dir.avro" --has-header $@ &&
    # resolved, was due to Spark 1.4+ requiring pyspark-shell for PYSPARK_SUBMIT_ARGS

    rm -fr "test-$dir.avro"
    if ../spark_json_to_avro.py -j data/multirecord.json -a "test-$dir.avro"; then
        echo "SUCCEEDED with header with Spark $SPARK_VERSION"
    else
        echo "FAILED with header with Spark $SPARK_VERSION"
        exit 1
    fi

    #../spark_json_to_avro.py -j data/multirecord.json -a "test-$dir.avro" -s Year:String,Make,Model,Dimension.0.Length:float &&
    #    echo "SUCCEEDED with header with Spark $SPARK_VERSION" ||
    #    { echo "FAILED with header with Spark $SPARK_VERSION"; exit 1; }
    # TODO: test using downloaded avro tools getschema or extend validate_avro.py + validate_parquet.py to have schema type checking

done
echo "SUCCESS"
