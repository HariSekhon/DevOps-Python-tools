#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-05-06 12:12:15 +0100 (Fri, 06 May 2016)
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
#                                   H B a s e
# ============================================================================ #
"

HBASE_HOST="${DOCKER_HOST:-${HBASE_HOST:-${HOST:-localhost}}}"
HBASE_HOST="${HBASE_HOST##*/}"
HBASE_HOST="${HBASE_HOST%%:*}"
export HBASE_HOST
export HBASE_STARGATE_PORT=8080
export HBASE_THRIFT_PORT=9090
export ZOOKEEPER_PORT=2181
export HBASE_PORTS="$ZOOKEEPER_PORT $HBASE_STARGATE_PORT 8085 $HBASE_THRIFT_PORT 9095 16000 16010 16201 16301"
export HBASE_TEST_PORTS="$ZOOKEEPER_PORT $HBASE_THRIFT_PORT"

#export HBASE_VERSIONS="0.96 0.98 1.0 1.1 1.2"
# don't work
#export HBASE_VERSIONS="0.98 0.96"
export HBASE_VERSIONS="1.0 1.1 1.2"

export DOCKER_IMAGE="harisekhon/hbase-dev"
export DOCKER_CONTAINER="hbase-test"

export MNTDIR=/pytools

if ! is_docker_available; then
    echo "WARNING: Docker not available, skipping HBase checks"
    exit 0
fi

startupwait=50

docker_exec(){
    docker exec -i "$DOCKER_CONTAINER" /bin/bash <<-EOF
    export JAVA_HOME=/usr
    $MNTDIR/$@
EOF
}

test_hbase(){
    local version="$1"
    hr
    echo "Setting up HBase $version test container"
    hr
    local DOCKER_OPTS="-v $srcdir/..:$MNTDIR"
    launch_container "$DOCKER_IMAGE:$version" "$DOCKER_CONTAINER" 2181 8080 8085 9090 9095 16000 16010 16201 16301
    when_ports_available $startupwait $HBASE_HOST $HBASE_TEST_PORTS
    echo "setting up test tables"
    uniq_val=$(< /dev/urandom tr -dc 'a-zA-Z0-9' | head -c32 || :)
    docker exec -i "$DOCKER_CONTAINER" /bin/bash <<-EOF
        export JAVA_HOME=/usr
        /hbase/bin/hbase shell <<-EOF2
        create 't1', 'cf1', { 'REGION_REPLICATION' => 1 }
        create 't2', 'cf2', { 'REGION_REPLICATION' => 1 }
        disable 't2'
        put 't1', 'r1', 'cf1:q1', '$uniq_val'
        put 't1', 'r2', 'cf1:q2', 'test'
        list
EOF2
EOF

    hr
    ./hbase_compact_tables.py -H $HBASE_HOST
    hr
    ./hbase_compact_tables.py -H $HBASE_HOST --regex .1
    hr
    docker_exec hbase_flush_tables.py
    hr
    docker_exec hbase_flush_tables.py -r .2
    hr

    delete_container
    echo
}

for version in $HBASE_VERSIONS; do
    test_hbase $version
done
