#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-05-06 12:12:15 +0100 (Fri, 06 May 2016)
#
#  https://github.com/harisekhon/devops-python-tools
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
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/.."

# shellcheck disable=SC1090
. "$srcdir/utils.sh"

# shellcheck disable=SC1090
. "$srcdir/../bash-tools/lib/docker.sh"

section "H B a s e"

HBASE_HOST="${DOCKER_HOST:-${HBASE_HOST:-${HOST:-localhost}}}"
HBASE_HOST="${HBASE_HOST##*/}"
HBASE_HOST="${HBASE_HOST%%:*}"
export HBASE_HOST
export HBASE_MASTER_PORT_DEFAULT=16010
export HBASE_REGIONSERVER_PORT_DEFAULT=16301
export HBASE_STARGATE_PORT_DEFAULT=8080
export HBASE_STARGATE_UI_PORT_DEFAULT=8085
export HBASE_THRIFT_PORT_DEFAULT=9090
export HBASE_THRIFT_UI_PORT_DEFAULT=9095
export ZOOKEEPER_PORT_DEFAULT=2181

export HBASE_VERSIONS="${*:-latest 0.96 0.98 1.0 1.1 1.2 1.3}"

check_docker_available

trap_debug_env hbase

# used by docker_exec
export DOCKER_MOUNT_DIR=/devops-python-tools
export DOCKER_JAVA_HOME=/usr

startupwait 30

test_hbase(){
    local version="$1"
    section2 "Setting up HBase $version test container"
    if [ -z "${KEEPDOCKER:-}" ]; then
        VERSION="$version" docker-compose down || :
    fi
    VERSION="$version" docker-compose up -d
    hr
    if [ "$version" = "0.96" ] ||
       [ "$version" = "0.98" ]; then
        export HBASE_MASTER_PORT_DEFAULT=60010
        export HBASE_REGIONSERVER_PORT_DEFAULT=60301
    fi
    echo "getting HBase dynamic port mappings:"
    docker_compose_port "HBase Master"
    docker_compose_port "HBase RegionServer"
    docker_compose_port "HBase Stargate"
    docker_compose_port "HBase Stargate UI"
    docker_compose_port "HBase Thrift"
    docker_compose_port "HBase Thrift UI"
    #docker_compose_port ZOOKEEPER_PORT "HBase ZooKeeper"
    export HBASE_PORTS="$HBASE_MASTER_PORT $HBASE_REGIONSERVER_PORT $HBASE_STARGATE_PORT $HBASE_STARGATE_UI_PORT $HBASE_THRIFT_PORT $HBASE_THRIFT_UI_PORT"
    hr
    # shellcheck disable=SC2086
    when_ports_available "$HBASE_HOST" $HBASE_PORTS
    hr
    if [ "${version:0:3}" = "0.9" ]; then
        when_url_content "http://$HBASE_HOST:$HBASE_MASTER_PORT/master-status" HBase
        hr
        when_url_content "http://$HBASE_HOST:$HBASE_REGIONSERVER_PORT/rs-status" HBase
    else
        when_url_content "http://$HBASE_HOST:$HBASE_MASTER_PORT/master-status" HMaster
        hr
        when_url_content "http://$HBASE_HOST:$HBASE_REGIONSERVER_PORT/rs-status" "HBase Region Server"
    fi
    hr
    when_url_content "http://$HBASE_HOST:$HBASE_STARGATE_UI_PORT/rest.jsp" "HBase.+REST"
    hr
    when_url_content "http://$HBASE_HOST:$HBASE_THRIFT_UI_PORT/thrift.jsp" "HBase.+Thrift"
    hr
    # ============================================================================ #
    if [ -z "${NOSETUP:-}" ]; then
        echo "setting up test tables:"
        uniq_val=$(< /dev/urandom tr -dc 'a-zA-Z0-9' 2>/dev/null | head -c32 || :)
        # gets ValueError: file descriptor cannot be a negative integer (-1), -T should be the workaround but hangs
        #docker-compose exec -T "$DOCKER_SERVICE" /bin/bash <<-EOF
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
        hr
    fi
    # ============================================================================ #
    if [ -n "${NOTESTS:-}" ]; then
        return
    fi
    # will otherwise pick up HBASE_HOST and use default port and return the real HBase Master
    # shellcheck disable=SC2097,SC2098
    HBASE_HOST='' HOST='' HBASE_MASTER_PORT="$HBASE_MASTER_PORT_DEFAULT" \
        ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_hbase_master.py 127.0.0.2 127.0.0.3 "$HBASE_HOST:$HBASE_REGIONSERVER_PORT"

    # if HBASE_PORT / --port is set to same as suffix then only outputs host not host:port
    # shellcheck disable=SC2097,SC2098
    HBASE_HOST='' HOST='' HBASE_MASTER_PORT="$HBASE_MASTER_PORT_DEFAULT" \
        run_grep "^$HBASE_HOST:$HBASE_MASTER_PORT$" ./find_active_hbase_master.py 127.0.0.2 "$HBASE_HOST:$HBASE_REGIONSERVER_PORT" 127.0.0.3 "$HBASE_HOST:$HBASE_MASTER_PORT"

    # ============================================================================ #

    ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_hbase_thrift.py 127.0.0.2 127.0.0.3 "$HBASE_HOST:$HBASE_REGIONSERVER_PORT"

    # if HBASE_PORT / --port is set to same as suffix then only outputs host not host:port
    run_grep "^$HBASE_HOST:$HBASE_THRIFT_UI_PORT$" ./find_active_hbase_thrift.py 127.0.0.2 "$HBASE_HOST:$HBASE_REGIONSERVER_PORT" 127.0.0.3 "$HBASE_HOST:$HBASE_THRIFT_UI_PORT"

    # ============================================================================ #

    ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_hbase_stargate.py 127.0.0.2 127.0.0.3 "$HBASE_HOST:$HBASE_REGIONSERVER_PORT"

    # if HBASE_PORT / --port is set to same as suffix then only outputs host not host:port
    run_grep "^$HBASE_HOST:$HBASE_STARGATE_UI_PORT$" ./find_active_hbase_stargate.py 127.0.0.2 "$HBASE_HOST:$HBASE_REGIONSERVER_PORT" 127.0.0.3 "$HBASE_HOST:$HBASE_STARGATE_UI_PORT"

    # ============================================================================ #

    export HBASE_THRIFT_SERVER_PORT="$HBASE_THRIFT_PORT"

    # ============================================================================ #
    run ./hbase_generate_data.py -n 10

    run_conn_refused ./hbase_generate_data.py -n 10

    echo "checking generate data fails with exit code 2 when table already exists on second run"
    run_fail 2 ./hbase_generate_data.py -n 10

    set +e
    echo "trying to send generated data to DisabledTable (times out):"
    run_fail 2 ./hbase_generate_data.py -n 10 -T DisabledTable --use-existing-table

    run ./hbase_generate_data.py -n 10 --drop-table

    run ./hbase_generate_data.py -n 10 --drop-table --skew

    run ./hbase_generate_data.py -n 10000 --use-existing-table --skew --skew-percent 50 -T UniformSplitTable

    run ./hbase_generate_data.py -n 10000 --use-existing-table -T HexStringSplitTable

    # ============================================================================ #

    run ./hbase_table_regions_by_regionserver.sh "$HBASE_HOST"

    run_usage ./hbase_table_regions_by_regionserver.sh

    # ============================================================================ #
    run_fail 3 ./hbase_compact_tables.py --list-tables

    run ./hbase_compact_tables.py -H "$HBASE_HOST"

    run_conn_refused ./hbase_compact_tables.py

    run ./hbase_compact_tables.py -r DisabledTable

    run ./hbase_compact_tables.py --regex .1

    # ============================================================================ #
    ERRCODE=3 docker_exec hbase_flush_tables.py --list-tables

    docker_exec hbase_flush_tables.py

    docker_exec hbase_flush_tables.py -r Disabled.*

    # ============================================================================ #
    run_fail 3 ./hbase_show_table_region_ranges.py --list-tables

    run_conn_refused ./hbase_show_table_region_ranges.py --list-tables

    echo "checking hbase_show_table_region_ranges.py against DisabledTable:"
    run ./hbase_show_table_region_ranges.py -T DisabledTable -vvv

    echo "checking hbase_show_table_region_ranges.py against EmptyTable:"
    run ./hbase_show_table_region_ranges.py -T EmptyTable -vvv

    run ./hbase_show_table_region_ranges.py -T HexStringSplitTable -v --short-region-name

    run ./hbase_show_table_region_ranges.py -T UniformSplitTable -v

    # ============================================================================ #
    run_fail 3 ./hbase_table_region_row_distribution.py --list-tables

    run_conn_refused ./hbase_table_region_row_distribution.py --list-tables

    echo "checking hbase_table_region_row_distribution.py against DisabledTable:"
    run_fail 2 ./hbase_table_region_row_distribution.py -T DisabledTable -vvv

    echo "checking hbase_table_region_row_distribution.py against EmptyTable:"
    run_fail 2 ./hbase_table_region_row_distribution.py -T EmptyTable -vvv

    run ./hbase_table_region_row_distribution.py -T UniformSplitTable -v --no-region-name

    run ./hbase_table_region_row_distribution.py -T HexStringSplitTable

    run ./hbase_table_region_row_distribution.py -T HexStringSplitTable -vv --short-region-name --sort server

    run ./hbase_table_region_row_distribution.py -T HexStringSplitTable --short-region-name --sort server --desc

    run ./hbase_table_region_row_distribution.py -T HexStringSplitTable --short-region-name --sort count

    run ./hbase_table_region_row_distribution.py -T HexStringSplitTable --short-region-name --sort count --desc

    # ============================================================================ #
    run_fail 3 ./hbase_table_row_key_distribution.py -T DisabledTable --list-tables

    echo "checking hbase_table_row_key_distribution.py against DisabledTable:"
    run_fail 2 ./hbase_table_row_key_distribution.py -T DisabledTable -vvv

    echo "checking hbase_table_row_key_distribution.py against EmptyTable:"
    run_fail 2 ./hbase_table_row_key_distribution.py -T EmptyTable -vvv

    run ./hbase_table_row_key_distribution.py -T UniformSplitTable -v --key-prefix-length 2

    run ./hbase_table_row_key_distribution.py -T UniformSplitTable --sort

    run ./hbase_table_row_key_distribution.py -T HexStringSplitTable --sort --desc

    run ./hbase_table_row_key_distribution.py -T HexStringSplitTable

    run_conn_refused ./hbase_table_row_key_distribution.py -T HexStringSplitTable

    # ============================================================================ #
    run ./hbase_region_requests.py -T HexStringSplitTable "$HBASE_HOST" -c 2
    run ./hbase_region_requests.py -T HexStringSplitTable "$HBASE_HOST" -c 2 --average
    run ./hbase_region_requests.py -T HexStringSplitTable "$HBASE_HOST" -c 2 --average --skip-zeros

    run ./hbase_region_requests.py -T HS_test_data "$HBASE_HOST" -c 2
    run ./hbase_region_requests.py -T HS_test_data "$HBASE_HOST" -c 2 --skip-zeros
    run ./hbase_region_requests.py -T HS_test_data "$HBASE_HOST" -c 2 --average

    run ./hbase_region_requests.py -T HS_test_data "$HBASE_HOST" --count 2 --interval 2

    run ./hbase_region_requests.py -T HS_test_data localhost "$HBASE_HOST" -c 2
    run ./hbase_region_requests.py -T HS_test_data localhost "$HBASE_HOST" --count 2 -i 2
    run ./hbase_region_requests.py -T HS_test_data localhost "$HBASE_HOST" -c 2 --average

    # ============================================================================ #
    run ./hbase_regionserver_requests.py "$HBASE_HOST" -c 1
    run ./hbase_regionserver_requests.py "$HBASE_HOST" -c 1 --average

    run ./hbase_regionserver_requests.py "$HBASE_HOST" -c 1 -T read,write,total
    run ./hbase_regionserver_requests.py "$HBASE_HOST" -c 1 --type read,write,total --average

    run ./hbase_regionserver_requests.py "$HBASE_HOST" --count 2 --interval 2

    run ./hbase_regionserver_requests.py localhost "$HBASE_HOST" -c 1
    run ./hbase_regionserver_requests.py localhost "$HBASE_HOST" --count 2 -i 2
    run ./hbase_regionserver_requests.py localhost "$HBASE_HOST" -c 1 --average

    # ============================================================================ #
    run ./hbase_regions_by_size.py "$HBASE_HOST"
    run ./hbase_regions_by_size.py "$HBASE_HOST" --smallest
    run ./hbase_regions_by_size.py "$HBASE_HOST" --human
    run ./hbase_regions_by_size.py "$HBASE_HOST" --human -s
    run ./hbase_regions_by_size.py "$HBASE_HOST" --human --top 10
    run ./hbase_regions_by_size.py "$HBASE_HOST" --human --top 10 --smallest

    run ./hbase_regions_by_memstore_size.py "$HBASE_HOST"
    run ./hbase_regions_by_memstore_size.py "$HBASE_HOST" --smallest
    run ./hbase_regions_by_memstore_size.py "$HBASE_HOST" --human
    run ./hbase_regions_by_memstore_size.py "$HBASE_HOST" --human -s
    run ./hbase_regions_by_memstore_size.py "$HBASE_HOST" --human --top 10
    run ./hbase_regions_by_memstore_size.py "$HBASE_HOST" --human --top 10 --smallest

    # ============================================================================ #
    run ./hbase_regions_least_used.py "$HBASE_HOST" -r 20000
    run ./hbase_regions_least_used.py "$HBASE_HOST" -r 0
    run ./hbase_regions_least_used.py "$HBASE_HOST" --human --requests 20000
    run ./hbase_regions_least_used.py "$HBASE_HOST" --human --requests 20000 --top 10

    [ -z "${KEEPDOCKER:-}" ] ||
    docker-compose down
    echo
}

run_test_versions HBase
