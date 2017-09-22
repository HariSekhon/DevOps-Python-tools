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
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$srcdir/.."

. "$srcdir/utils.sh"

section "H a d o o p"

export HADOOP_VERSIONS="${@:-${HADOOP_VERSIONS:-latest 2.5 2.6 2.7}}"

HADOOP_HOST="${DOCKER_HOST:-${HADOOP_HOST:-${HOST:-localhost}}}"
HADOOP_HOST="${HADOOP_HOST##*/}"
HADOOP_HOST="${HADOOP_HOST%%:*}"
export HADOOP_HOST
# don't need these each script should fall back to using HADOOP_HOST secondary if present
# TODO: make sure new script for block balance does this
#export HADOOP_NAMENODE_HOST="$HADOOP_HOST"
#export HADOOP_DATANODE_HOST="$HADOOP_HOST"
#export HADOOP_YARN_RESOURCE_MANAGER_HOST="$HADOOP_HOST"
#export HADOOP_YARN_NODE_MANAGER_HOST="$HADOOP_HOST"
export HADOOP_NAMENODE_PORT_DEFAULT="50070"
export HADOOP_DATANODE_PORT_DEFAULT="50075"
export HADOOP_YARN_RESOURCE_MANAGER_PORT_DEFAULT="8088"
export HADOOP_YARN_NODE_MANAGER_PORT_DEFAULT="8042"
#export HADOOP_PORTS="8042 8088 50010 50020 50070 50075 50090"

# not used any more, see instead tests/docker/hadoop-docker-compose.yml
#export DOCKER_IMAGE="harisekhon/hadoop"
#export MNTDIR="/py"

# NN comes up, but RM is really slow to come up, need this 80 secs not 30
startupwait 80

check_docker_available

trap_debug_env hadoop

docker_exec(){
    #docker-compose exec "$DOCKER_SERVICE" $MNTDIR/$@
    echo "docker exec 'pytools_${DOCKER_SERVICE}_1' $MNTDIR/$@"
    docker exec "pytools_${DOCKER_SERVICE}_1" $MNTDIR/$@
}

test_hadoop(){
    local version="$1"
    section2 "Setting up Hadoop $version test container"
    #DOCKER_OPTS="-v $srcdir2/..:$MNTDIR"
    #launch_container "$DOCKER_IMAGE:$version" "$DOCKER_CONTAINER" $HADOOP_PORTS
    VERSION="$version" docker-compose up -d
    echo "getting Hadoop dynamic port mappings"
    printf "getting HDFS NN port => "
    export HADOOP_NAMENODE_PORT="`docker-compose port "$DOCKER_SERVICE" "$HADOOP_NAMENODE_PORT_DEFAULT" | sed 's/.*://'`"
    echo "$HADOOP_NAMENODE_PORT"
    printf "getting HDFS DN port => "
    export HADOOP_DATANODE_PORT="`docker-compose port "$DOCKER_SERVICE" "$HADOOP_DATANODE_PORT_DEFAULT" | sed 's/.*://'`"
    echo "$HADOOP_DATANODE_PORT"
    printf  "getting Yarn RM port => "
    export HADOOP_YARN_RESOURCE_MANAGER_PORT="`docker-compose port "$DOCKER_SERVICE" "$HADOOP_YARN_RESOURCE_MANAGER_PORT_DEFAULT" | sed 's/.*://'`"
    echo "$HADOOP_YARN_RESOURCE_MANAGER_PORT"
    printf "getting Yarn NM port => "
    export HADOOP_YARN_NODE_MANAGER_PORT="`docker-compose port "$DOCKER_SERVICE" "$HADOOP_YARN_NODE_MANAGER_PORT_DEFAULT" | sed 's/.*://'`"
    echo "$HADOOP_YARN_NODE_MANAGER_PORT"
    #local hadoop_ports=`{ for x in $HADOOP_PORTS; do docker-compose port "$DOCKER_SERVICE" "$x"; done; } | sed 's/.*://'`
    export HADOOP_PORTS="$HADOOP_NAMENODE_PORT $HADOOP_DATANODE_PORT $HADOOP_YARN_RESOURCE_MANAGER_PORT $HADOOP_YARN_NODE_MANAGER_PORT"
    when_ports_available "$startupwait" "$HADOOP_HOST" $HADOOP_PORTS
cat >/dev/null <<EOFCOMMENTED
    echo "setting up HDFS for tests"
    #docker-compose exec "$DOCKER_SERVICE" /bin/bash <<-EOF
    docker exec -i "nagiosplugins_${DOCKER_SERVICE}_1" /bin/bash <<-EOF
        export JAVA_HOME=/usr
        echo "leaving safe mode"
        hdfs dfsadmin -safemode leave
        echo "removing old hdfs file /tmp/test.txt if present"
        hdfs dfs -rm -f /tmp/test.txt &>/dev/null
        echo "creating test hdfs file /tmp/test.txt"
        echo content | hdfs dfs -put - /tmp/test.txt
        # if using wrong port like 50075 ot 50010 then you'll get this exception
        # triggerBlockReport error: java.io.IOException: Failed on local exception: com.google.protobuf.InvalidProtocolBufferException: Protocol message end-group tag did not match expected tag.; Host Details : local host is: "94bab7680584/172.19.0.2"; destination host is: "localhost":50075;
        # this doesn't help get Total Blocks in /blockScannerReport for ./check_hadoop_datanode_blockcount.pl, looks like that information is simply not exposed like that any more
        #hdfs dfsadmin -triggerBlockReport localhost:50020
        echo "dumping fsck log"
        hdfs fsck / &> /tmp/hdfs-fsck.log.tmp && tail -n30 /tmp/hdfs-fsck.log.tmp > /tmp/hdfs-fsck.log
        exit
EOF
EOFCOMMENTED
    echo
    if [ -n "${NOTESTS:-}" ]; then
        exit 0
    fi
    hr
    if [ "$version" = "latest" ]; then
        local version=".*"
    fi
    # docker-compose exec returns $'hostname\r' but not in shell
#    hostname="$(docker-compose exec "$DOCKER_SERVICE" hostname | tr -d '$\r')"
#    if [ -z "$hostname" ]; then
#        echo 'Failed to determine hostname of container via docker-compose exec, cannot continue with tests!'
#        exit 1
#    fi
    hr
    check_output "NO_AVAILABLE_SERVER" ./find_active_hadoop_namenode.py 127.0.0.2 127.0.0.3
    hr
    check_output "$HADOOP_HOST:$HADOOP_NAMENODE_PORT" ./find_active_hadoop_namenode.py 127.0.0.2 127.0.0.3 "$HADOOP_HOST:$HADOOP_NAMENODE_PORT"
    hr
    #echo "waiting 10 secs for Yarn RM to come up to test version"
    #sleep 10
    local count=0
    local max_tries=20
    while true; do
        echo "waiting for Yarn RM cluster page to come up to test for active resource manager..."
        # intentionally being a bit loose here, if content has changed I would rather it be flagged as up and the plugin fail to parse which is more a more accurate error
        if curl -s "$HADOOP_HOST:$HADOOP_YARN_RESOURCE_MANAGER_PORT/ws/v1/cluster" | grep -qi hadoop; then
            break
        fi
        let count+=1
        if [ $count -ge 20 ]; then
            echo "giving up after $max_tries tries"
            break
        fi
        sleep 1
    done
    hr
    check_output "NO_AVAILABLE_SERVER" ./find_active_hadoop_yarn_resource_manager.py 127.0.0.2 127.0.0.3
    hr
    check_output "$HADOOP_HOST:$HADOOP_YARN_RESOURCE_MANAGER_PORT" ./find_active_hadoop_yarn_resource_manager.py 127.0.0.2 127.0.0.3 "$HADOOP_HOST:$HADOOP_YARN_RESOURCE_MANAGER_PORT"
    hr
    #delete_container
    docker-compose down
    echo
    echo
}

run_test_versions Hadoop
