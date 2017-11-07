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

section "H B a s e"

HBASE_HOST="${DOCKER_HOST:-${HBASE_HOST:-${HOST:-localhost}}}"
HBASE_HOST="${HBASE_HOST##*/}"
HBASE_HOST="${HBASE_HOST%%:*}"
export HBASE_HOST
export HBASE_MASTER_PORT_DEFAULT=16010
export HBASE_REGIONSERVER_PORT_DEFAULT=16301
export HBASE_STARGATE_PORT_DEFAULT=8080
export HBASE_THRIFT_PORT_DEFAULT=9090
export ZOOKEEPER_PORT_DEFAULT=2181

export HBASE_VERSIONS="${@:-latest 0.96 0.98 1.0 1.1 1.2 1.3}"

check_docker_available

trap_debug_env hbase

# used by docker_exec
export DOCKER_MOUNT_DIR=/pytools
export DOCKER_JAVA_HOME=/usr

startupwait 30

test_hbase(){
    local version="$1"
    section2 "Setting up HBase $version test container"
    if [ -z "${KEEPDOCKER:-}" ]; then
        VERSION="$version" docker-compose down || :
    fi
    VERSION="$version" docker-compose up -d
    if [ "$version" = "0.96" -o "$version" = "0.98" ]; then
        local export HBASE_MASTER_PORT_DEFAULT=60010
        local export HBASE_REGIONSERVER_PORT_DEFAULT=60301
    fi
    echo "getting HBase dynamic port mappings:"
    docker_compose_port "HBase Master"
    docker_compose_port "HBase RegionServer"
    docker_compose_port "HBase Stargate"
    docker_compose_port "HBase Thrift"
    #docker_compose_port ZOOKEEPER_PORT "HBase ZooKeeper"
    export HBASE_PORTS="$HBASE_MASTER_PORT $HBASE_REGIONSERVER_PORT $HBASE_STARGATE_PORT $HBASE_THRIFT_PORT"
    hr
    when_ports_available "$HBASE_HOST" $HBASE_PORTS
    hr
    when_url_content "http://$HBASE_HOST:$HBASE_MASTER_PORT/master-status" hbase
    hr
    when_url_content "http://$HBASE_HOST:$HBASE_REGIONSERVER_PORT/rs-status" hbase
    hr
    # ============================================================================ #
    echo "setting up test tables"
    uniq_val=$(< /dev/urandom tr -dc 'a-zA-Z0-9' 2>/dev/null | head -c32 || :)
    # gets ValueError: file descriptor cannot be a negative integer (-1), -T should be the workaround but hangs
    #docker-compose exec -T "$DOCKER_SERVICE" /bin/bash <<-EOF
    if [ -z "${NOSETUP:-}" ]; then
    docker exec -i "$DOCKER_CONTAINER" /bin/bash <<-EOF
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
    fi
    # ============================================================================ #
    if [ -n "${NOTESTS:-}" ]; then
        return
    fi
    hr
    # will otherwise pick up HBASE_HOST and use default port and return the real HBase Master
    HBASE_HOST='' HOST='' HBASE_MASTER_PORT="$HBASE_MASTER_PORT_DEFAULT" \
        run_output "NO_AVAILABLE_SERVER" ./find_active_hbase_master.py 127.0.0.2 127.0.0.3 "$HBASE_HOST:$HBASE_REGIONSERVER_PORT"
    hr
    # if HBASE_PORT / --port is set to same as suffix then only outputs host not host:port
    HBASE_HOST='' HOST='' HBASE_MASTER_PORT="$HBASE_MASTER_PORT_DEFAULT" \
        run_output "$HBASE_HOST:$HBASE_MASTER_PORT" ./find_active_hbase_master.py 127.0.0.2 "$HBASE_HOST:$HBASE_REGIONSERVER_PORT" 127.0.0.3 "$HBASE_HOST:$HBASE_MASTER_PORT"
    hr
    export HBASE_THRIFT_SERVER_PORT="$HBASE_THRIFT_PORT"
    hr
    # ============================================================================ #
    run ./hbase_generate_data.py -n 10
    hr
    run_conn_refused ./hbase_generate_data.py -n 10
    hr
    echo "checking generate data fails with exit code 2 when table already exists on second run"
    run_fail 2 ./hbase_generate_data.py -n 10
    hr
    set +e
    echo "trying to send generated data to DisabledTable (times out):"
    run_fail 2 ./hbase_generate_data.py -n 10 -T DisabledTable --use-existing-table
    hr
    run ./hbase_generate_data.py -n 10 --drop-table
    hr
    run ./hbase_generate_data.py -n 10 --drop-table --skew
    hr
    run ./hbase_generate_data.py -n 10000 --use-existing-table --skew --skew-percent 50 -T UniformSplitTable
    hr
    run ./hbase_generate_data.py -n 10000 --use-existing-table -T HexStringSplitTable
    hr
    # ============================================================================ #
    run_fail 3 ./hbase_compact_tables.py --list-tables
    hr
    run ./hbase_compact_tables.py -H "$HBASE_HOST"
    hr
    run_conn_refused ./hbase_compact_tables.py
    hr
    run ./hbase_compact_tables.py -r DisabledTable
    hr
    run ./hbase_compact_tables.py --regex .1
    hr
    # ============================================================================ #
    ERRCODE=3 docker_exec hbase_flush_tables.py --list-tables
    hr
    docker_exec hbase_flush_tables.py
    hr
    docker_exec hbase_flush_tables.py -r Disabled.*
    hr
    # ============================================================================ #
    run_fail 3 ./hbase_show_table_region_ranges.py --list-tables
    hr
    run_conn_refused ./hbase_show_table_region_ranges.py --list-tables
    hr
    echo "checking hbase_show_table_region_ranges.py against DisabledTable:"
    run ./hbase_show_table_region_ranges.py -T DisabledTable -vvv
    hr
    echo "checking hbase_show_table_region_ranges.py against EmptyTable:"
    run ./hbase_show_table_region_ranges.py -T EmptyTable -vvv
    hr
    run ./hbase_show_table_region_ranges.py -T HexStringSplitTable -v --short-region-name
    hr
    run ./hbase_show_table_region_ranges.py -T UniformSplitTable -v
    hr
    # ============================================================================ #
    run_fail 3 ./hbase_calculate_table_region_row_distribution.py --list-tables
    hr
    run_conn_refused ./hbase_calculate_table_region_row_distribution.py --list-tables
    hr
    echo "checking hbase_calculate_table_region_row_distribution.py against DisabledTable:"
    run_fail 2 ./hbase_calculate_table_region_row_distribution.py -T DisabledTable -vvv
    hr
    echo "checking hbase_calculate_table_region_row_distribution.py against EmptyTable:"
    run_fail 2 ./hbase_calculate_table_region_row_distribution.py -T EmptyTable -vvv
    hr
    run ./hbase_calculate_table_region_row_distribution.py -T UniformSplitTable -v --no-region-name
    hr
    run ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable
    hr
    run ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable -vv --short-region-name --sort server
    hr
    run ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable --short-region-name --sort server --desc
    hr
    run ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable --short-region-name --sort count
    hr
    run ./hbase_calculate_table_region_row_distribution.py -T HexStringSplitTable --short-region-name --sort count --desc
    hr
    # ============================================================================ #
    run_fail 3 ./hbase_calculate_table_row_key_distribution.py -T DisabledTable --list-tables
    hr
    echo "checking hbase_calculate_table_row_key_distribution.py against DisabledTable:"
    run_fail 2 ./hbase_calculate_table_row_key_distribution.py -T DisabledTable -vvv
    hr
    echo "checking hbase_calculate_table_row_key_distribution.py against EmptyTable:"
    run_fail 2 ./hbase_calculate_table_row_key_distribution.py -T EmptyTable -vvv
    hr
    run ./hbase_calculate_table_row_key_distribution.py -T UniformSplitTable -v --key-prefix-length 2
    hr
    run ./hbase_calculate_table_row_key_distribution.py -T UniformSplitTable --sort
    hr
    run ./hbase_calculate_table_row_key_distribution.py -T HexStringSplitTable --sort --desc
    hr
    run ./hbase_calculate_table_row_key_distribution.py -T HexStringSplitTable
    hr
    run_conn_refused ./hbase_calculate_table_row_key_distribution.py -T HexStringSplitTable
    hr

    docker-compose down
    echo
}

run_test_versions HBase
