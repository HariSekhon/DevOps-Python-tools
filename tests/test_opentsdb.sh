#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-10-10 11:54:19 +0100 (Mon, 10 Oct 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

srcdir2="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir2/.."

. "$srcdir2/utils.sh"

srcdir="$srcdir2"

echo "
# ============================================================================ #
#                                O p e n T S D B
# ============================================================================ #
"

OPENTSDB_HOST="${DOCKER_HOST:-${OPENTSDB_HOST:-${HOST:-localhost}}}"
OPENTSDB_HOST="${OPENTSDB_HOST##*/}"
OPENTSDB_HOST="${OPENTSDB_HOST%%:*}"
export OPENTSDB_HOST
export HBASE_STARGATE_PORT=8080
export HBASE_THRIFT_PORT=9090
export ZOOKEEPER_PORT=2181
export OPENTSDB_PORTS="$ZOOKEEPER_PORT $HBASE_STARGATE_PORT 8085 $HBASE_THRIFT_PORT 9095 3000 16000 16010 16201 16301"
export OPENTSDB_TEST_PORTS="$ZOOKEEPER_PORT $HBASE_THRIFT_PORT 3000"

export OPENTSDB_VERSIONS="${@:-latest}"

#export DOCKER_IMAGE="opower/opentsdb"
#export DOCKER_IMAGE="petergrace/opentsdb-docker"
export DOCKER_CONTAINER="opentsdb-test"

export MNTDIR=/pytools

export DATA_FILE='tests/data/opentsdb_data.txt'

#if ! is_docker_available; then
#    echo "WARNING: Docker not available, skipping OpenTSDB checks"
#    exit 0
#fi

startupwait=50

docker_exec(){
    docker exec -i "$DOCKER_CONTAINER" /bin/bash <<-EOF
    export JAVA_HOME=/usr
    $MNTDIR/$@
EOF
}

generate_test_data(){
    if [ -f "$DATA_FILE" ]; then
        echo "data file '$DATA_FILE' already exists, not regenerating"
        return
    fi
    echo "generating opentsdb test data => $DATA_FILE"
    local chars
    local ts
    local metric
    #chars="$(echo {A..Z} {a..z} {0..9})"
    chars=$(echo {A..Z} | tr -d ' ')
    ts="$(date '+%s')"
    for x in {1..100}; do
        for y in {1..1000}; do
            metric="metric${chars:$((RANDOM % ${#chars})):1}"
            for z in {1..5}; do
                echo "ship${RANDOM:0:3} $(($ts + $RANDOM)) $RANDOM id=$metric crew=$z"
            done
        done
    done > "$DATA_FILE"
}

generate_test_data

test_opentsdb(){
    local version="$1"
    #hr
    #echo "Setting up OpenTSDB $version test container"
    #hr
    #local DOCKER_OPTS="-v $srcdir/..:$MNTDIR"
    #launch_container "$DOCKER_IMAGE:$version" "$DOCKER_CONTAINER" 2181 8080 8085 9090 9095 16000 16010 16201 16301
    #when_ports_available $startupwait $OPENTSDB_HOST $OPENTSDB_TEST_PORTS
    if [ -n "${NOTESTS:-}" ]; then
        return
    fi
    hr
    echo "testing from data file:"
    ./opentsdb_calculate_import_metric_distribution.py -K 1 -vv "$DATA_FILE"
    hr
    echo "testing from STDIN:"
    ./opentsdb_calculate_import_metric_distribution.py -K 1 -vv - < "$DATA_FILE"
    hr
    echo "testing reverse sort on count:"
    ./opentsdb_calculate_import_metric_distribution.py -K 3 -d "$DATA_FILE"
    hr
    echo "testing skipping error lines:"
    ./opentsdb_calculate_import_metric_distribution.py -K 4 --skip-errors - <<EOF
shipCustom $(date +%s) 10 id=metric1
made up error line
EOF
    hr
    echo "testing from data file and STDIN at the same time:"
    ./opentsdb_calculate_import_metric_distribution.py --key-prefix-length 7 "$DATA_FILE" - < "$DATA_FILE"
    hr

    #delete_container
    echo
}

for version in $OPENTSDB_VERSIONS; do
    test_opentsdb $version
done
if [ -z "${NODELETE:-}" ]; then
    echo -n "removing test data: "
    rm -vf "$DATA_FILE"
    echo; echo
fi
echo "All OpenTSDB tests succeeded"
echo
