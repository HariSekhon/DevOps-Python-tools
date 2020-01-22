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
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$srcdir/.."

# shellcheck disable=SC1090
. "$srcdir/utils.sh"

section "H a d o o p"

# find_active_hadoop_namenode.py doesn't work on Hadoop 2.2 as the JMX bean isn't present
export HADOOP_VERSIONS="${*:-${HADOOP_VERSIONS:-latest 2.3 2.4 2.5 2.6 2.7 2.8}}"

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

# NN comes up, but RM is really slow to come up, give 80 secs not 50
startupwait 80

check_docker_available

trap_debug_env hadoop

test_hadoop(){
    local version="$1"
    section2 "Setting up Hadoop $version test container"
    VERSION="$version" docker-compose up -d
    hr
    echo "getting Hadoop dynamic port mappings:"
    docker_compose_port HADOOP_NAMENODE_PORT "HDFS NN"
    docker_compose_port HADOOP_DATANODE_PORT "HDFS DN"
    docker_compose_port HADOOP_YARN_RESOURCE_MANAGER_PORT "Yarn RM"
    docker_compose_port HADOOP_YARN_NODE_MANAGER_PORT "Yarn NM"
    export HADOOP_PORTS="$HADOOP_NAMENODE_PORT $HADOOP_DATANODE_PORT $HADOOP_YARN_RESOURCE_MANAGER_PORT $HADOOP_YARN_NODE_MANAGER_PORT"
    hr
    # shellcheck disable=SC2086
    when_ports_available "$HADOOP_HOST" $HADOOP_PORTS
    hr
    # don't use the worker nodes so not testing for their availability
    echo "waiting for NN dfshealth page to come up before testing for active namenode:"
    if [[ "$version" =~ ^2\.[2-4]$ ]]; then
        when_url_content "$HADOOP_HOST:$HADOOP_NAMENODE_PORT/dfshealth.jsp" 'Hadoop NameNode'
        #echo "waiting for DN page to come up:"
        #hr
        # Hadoop 2.2 is broken, just check for WEB-INF, 2.3 redirects so check for url
        #when_url_content "$HADOOP_HOST:$HADOOP_DATANODE_PORT" 'WEB-INF|url=dataNodeHome.jsp'
    else
        when_url_content "$HADOOP_HOST:$HADOOP_NAMENODE_PORT/dfshealth.html" 'NameNode Journal Status'
        #hr
        #echo "waiting for DN page to come up:"
        # Hadoop 2.8 uses /datanode.html but this isn't available on older versions eg. 2.6 so change the regex to find the redirect in 2.8 instead
        #when_url_content "$HADOOP_HOST:$HADOOP_DATANODE_PORT" 'DataNode on|url=datanode\.html'
    fi
    hr
    echo "waiting for RM cluster page to come up before testing for active resource manager:"
    when_url_content "$HADOOP_HOST:$HADOOP_YARN_RESOURCE_MANAGER_PORT/ws/v1/cluster" resourceManager
    hr
    #echo "waiting for NM node page to come up:"
    # Hadoop 2.8 content = NodeManager information
    #when_url_content "$HADOOP_HOST:$HADOOP_YARN_NODE_MANAGER_PORT/node" 'Node Manager Version|NodeManager information'
    hr
    [ -z "${NOSETUP:-}" ] &&
    cat >/dev/null <<EOFCOMMENTED
    echo "setting up HDFS for tests"
    #docker-compose exec "$DOCKER_SERVICE" /bin/bash <<-EOF
    docker exec -i "$DOCKER_CONTAINER" /bin/bash <<-EOF
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
    hr
    if [ -n "${NOTESTS:-}" ]; then
        exit 0
    fi
    if [ "$version" = "latest" ]; then
        local version=".*"
    fi
    # docker-compose exec returns $'hostname\r' but not in shell
#    hostname="$(docker-compose exec "$DOCKER_SERVICE" hostname | tr -d '$\r')"
#    if [ -z "$hostname" ]; then
#        echo 'Failed to determine hostname of container via docker-compose exec, cannot continue with tests!'
#        exit 1
#    fi

    # Docker maps all these 127.0.0.2, 127.0.0.3 etc to go to docker port mappings so is there is a container running it finds it accidentally
    # therefore reset the HADOOP PORTS to point to something that should get connection refused like port 1 and so that the failure hosts still fail and return only the expected correct host
    HADOOP_NAMENODE_PORT=1 ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_hadoop_namenode.py 127.0.0.2 127.0.0.3 "$HADOOP_HOST:$HADOOP_DATANODE_PORT"

    # shellcheck disable=SC2097,SC2098
    HADOOP_NAMENODE_PORT=1 run_grep "^$HADOOP_HOST:$HADOOP_NAMENODE_PORT$" ./find_active_hadoop_namenode.py 127.0.0.2 "$HADOOP_HOST:$HADOOP_DATANODE_PORT" 127.0.0.3 "$HADOOP_HOST:$HADOOP_NAMENODE_PORT"

    HADOOP_YARN_RESOURCE_MANAGER_PORT=1 ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_hadoop_yarn_resource_manager.py 127.0.0.2 127.0.0.3 "$HADOOP_HOST:$HADOOP_YARN_NODE_MANAGER_PORT"

    # shellcheck disable=SC2097,SC2098
    HADOOP_YARN_RESOURCE_MANAGER_PORT=1 run_grep "^$HADOOP_HOST:$HADOOP_YARN_RESOURCE_MANAGER_PORT$" ./find_active_hadoop_yarn_resource_manager.py 127.0.0.2 "$HADOOP_HOST:$HADOOP_YARN_NODE_MANAGER_PORT" 127.0.0.3 "$HADOOP_HOST:$HADOOP_YARN_RESOURCE_MANAGER_PORT"
    [ -z "${KEEPDOCKER:-}" ] ||
    docker-compose down
    echo
    echo
}

run_test_versions Hadoop
