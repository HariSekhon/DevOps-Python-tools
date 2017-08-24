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
. "$srcdir2/../bash-tools/docker.sh"

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

export HBASE_VERSIONS="${@:-0.96 0.98 1.0 1.1 1.2 latest}"

check_docker_available

export MNTDIR="/pytools"

startupwait=50

docker_exec(){
    # gets ValueError: file descriptor cannot be a negative integer (-1), -T should be the workaround but hangs
    #docker-compose exec -T "$DOCKER_SERVICE" /bin/bash <<-EOF
    docker exec -i "${COMPOSE_PROJECT_NAME:-docker}_${DOCKER_SERVICE}_1" /bin/bash <<-EOF
    export JAVA_HOME=/usr
    $MNTDIR/$@
EOF
}

test_hbase(){
    local version="$1"
    section2 "Setting up HBase $version test container"
    #local DOCKER_OPTS="-v $srcdir/..:$MNTDIR"
    #launch_container "$DOCKER_IMAGE:$version" "$DOCKER_CONTAINER" 2181 8080 8085 9090 9095 16000 16010 16201 16301
    VERSION="$version" docker-compose up -d
    local HBASE_STARGATE_PORT="`docker-compose port "$DOCKER_SERVICE" "$HBASE_STARGATE_PORT" | sed 's/.*://'`"
    local HBASE_THRIFT_PORT="`docker-compose port "$DOCKER_SERVICE" "$HBASE_THRIFT_PORT" | sed 's/.*://'`"
    local ZOOKEEPER_PORT="`docker-compose port "$DOCKER_SERVICE" "$ZOOKEEPER_PORT" | sed 's/.*://'`"
    #hbase_ports=`{ for x in $HBASE_PORTS; do docker-compose port "$DOCKER_SERVICE" "$x"; done; } | sed 's/.*://'`
    hbase_ports="$HBASE_STARGATE_PORT $HBASE_THRIFT_PORT $ZOOKEEPER_PORT"
    when_ports_available "$startupwait" "$HBASE_HOST" $hbase_ports
    #when_ports_available $startupwait $HBASE_HOST $HBASE_TEST_PORTS
    echo "setting up test tables"
    uniq_val=$(< /dev/urandom tr -dc 'a-zA-Z0-9' 2>/dev/null | head -c32 || :)
    # gets ValueError: file descriptor cannot be a negative integer (-1), -T should be the workaround but hangs
    #docker-compose exec -T "$DOCKER_SERVICE" /bin/bash <<-EOF
    docker exec -i "${COMPOSE_PROJECT_NAME:-docker}_${DOCKER_SERVICE}_1" /bin/bash <<-EOF
        export JAVA_HOME=/usr
        /hbase/bin/hbase shell <<-EOF2
            create 't1', 'cf1', { 'REGION_REPLICATION' => 1 }
            create 'EmptyTable', 'cf2', { 'REGION_REPLICATION' => 1 }
            create 'DisabledTable', 'cf3', { 'REGION_REPLICATION' => 1 }
            disable 'DisabledTable'
            put 't1', 'r1', 'cf1:q1', '$uniq_val'
            put 't1', 'r2', 'cf1:q2', 'test'
            list
EOF2
        hbase org.apache.hadoop.hbase.util.RegionSplitter UniformSplitTable UniformSplit -c 100 -f cf1
        hbase org.apache.hadoop.hbase.util.RegionSplitter HexStringSplitTable HexStringSplit -c 100 -f cf1
        # the above may fail, ensure we continue to try the tests
        exit 0
EOF
    if [ -n "${NOTESTS:-}" ]; then
        return
    fi
    export HBASE_THRIFT_SERVER_PORT="$HBASE_THRIFT_PORT"
    hr
    ./hbase_generate_data.py -n 10
    hr
    set +e
    ./hbase_generate_data.py -n 10
    check_exit_code 2
    set -e
    hr
    set +e
    echo "trying to send generated data to DisabledTable (times out):"
    ./hbase_generate_data.py -n 10 -T DisabledTable -X
    check_exit_code 2
    set -e
    hr
    ./hbase_generate_data.py -n 10 -d
    hr
    ./hbase_generate_data.py -n 10 -d -s
    hr
    ./hbase_generate_data.py -n 10000 -X -s --pc 50 -T UniformSplitTable
    hr
    ./hbase_generate_data.py -n 10000 -X -T HexStringSplitTable
    hr
    set +e
    ./hbase_compact_tables.py --list-tables
    check_exit_code 3
    set -e
    hr
    ./hbase_compact_tables.py -H $HBASE_HOST
    hr
    ./hbase_compact_tables.py -r DisabledTable
    hr
    ./hbase_compact_tables.py --regex .1
    hr
    set +e
    docker_exec hbase_flush_tables.py --list-tables
    check_exit_code 3
    set -e
    hr
    docker_exec hbase_flush_tables.py
    hr
    docker_exec hbase_flush_tables.py -r Disabled.*
    hr
    set +e
    ./hbase_show_table_region_ranges.py --list-tables
    check_exit_code 3
    set -e
    hr
    echo "checking hbase_show_table_region_ranges.py against DisabledTable"
    ./hbase_show_table_region_ranges.py -T DisabledTable -vvv
    hr
    echo "checking hbase_show_table_region_ranges.py against EmptyTable"
    ./hbase_show_table_region_ranges.py -T EmptyTable -vvv
    hr
    ./hbase_show_table_region_ranges.py -T HexStringSplitTable -v --short-region-name
    hr
    ./hbase_show_table_region_ranges.py -T UniformSplitTable -v
    hr
    set +e
    ./hbase_calculate_table_region_row_distribution.py --list-tables
    check_exit_code 3
    set -e
    hr
    echo "checking hbase_calculate_table_region_row_distribution.py against DisabledTable"
    set +e
    ./hbase_calculate_table_region_row_distribution.py -T DisabledTable -vvv
    check_exit_code 2
    set -e
    hr
    echo "checking hbase_calculate_table_region_row_distribution.py against EmptyTable"
    set +e
    ./hbase_calculate_table_region_row_distribution.py -T EmptyTable -vvv
    check_exit_code 2
    set -e
    hr
    ./hbase_calculate_table_region_row_distribution.py -T UniformSplitTable -v --no-region-name
    hr
    ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable
    hr
    ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable -vv --short-region-name --sort server
    hr
    ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable --short-region-name --sort server --desc
    hr
    ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable --short-region-name --sort count
    hr
    ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable --short-region-name --sort count --desc
    hr
    echo "checking hbase_calculate_table_row_key_distribution.py against DisabledTable"
    set +e
    ./hbase_calculate_table_row_key_distribution.py -T DisabledTable -vvv
    check_exit_code 2
    set -e
    hr
    echo "checking hbase_calculate_table_row_key_distribution.py against EmptyTable"
    set +e
    ./hbase_calculate_table_row_key_distribution.py -T EmptyTable -vvv
    check_exit_code 2
    set -e
    hr
    ./hbase_calculate_table_row_key_distribution.py -T UniformSplitTable -v --key-prefix-length 2
    hr
    ./hbase_calculate_table_row_key_distribution.py -T UniformSplitTable --sort
    hr
    ./hbase_calculate_table_row_key_distribution.py -T HexStringSplitTable --sort --desc
    hr
    ./hbase_calculate_table_row_key_distribution.py -T HexStringSplitTable
    hr

    #delete_container
    docker-compose down
    echo
}

for version in $HBASE_VERSIONS; do
    test_hbase $version
done
echo "All HBase Tests Succeeded"
echo
