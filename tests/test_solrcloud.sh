#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-22 21:13:49 +0000 (Fri, 22 Jan 2016)
#
#  https://github.com/harisekhon/nagios-plugins
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/.."

# shellcheck disable=SC1091
. ./tests/utils.sh

section "S o l r C l o u d"

export SOLRCLOUD_VERSIONS="${*:-${SOLRCLOUD_VERSIONS:-latest 4.10 5.5 6.0 6.1 6.2 6.3 6.4 6.5 6.6}}"

SOLR_HOST="${DOCKER_HOST:-${SOLR_HOST:-${HOST:-localhost}}}"
SOLR_HOST="${SOLR_HOST##*/}"
export SOLR_HOST="${SOLR_HOST%%:*}"
export SOLR_PORT_DEFAULT="${SOLR_PORT:-8983}"
export SOLR_ZOOKEEPER_PORT_DEFAULT="${SOLR_ZOOKEEPER_PORT:-9983}"
export SOLR_PORTS="$SOLR_PORT_DEFAULT 8984 $SOLR_ZOOKEEPER_PORT_DEFAULT"
export ZOOKEEPER_HOST="$SOLR_HOST"

export SOLR_HOME="/solr"

startupwait 30

check_docker_available

trap_debug_env solr zookeeper

test_solrcloud(){
    local version="$1"
    # SolrCloud 4.x needs some different args / locations
    if [ "${version:0:1}" = 4 ]; then
        export SOLR_COLLECTION="collection1"
    else
        export SOLR_COLLECTION="gettingstarted"
    fi
    section2 "Setting up SolrCloud $version docker test container"
    VERSION="$version" docker-compose up -d
    echo "getting SolrCloud dynamic port mappings:"
    docker_compose_port SOLR_PORT "Solr HTTP"
    #docker_compose_port "ZooKeeper"
    hr
    when_ports_available "$SOLR_HOST" "$SOLR_PORT" # "$SOLR_ZOOKEEPER_PORT"
    hr
    when_url_content "http://$SOLR_HOST:$SOLR_PORT/solr/" "Solr Admin"
    hr
    local DOCKER_CONTAINER
    DOCKER_CONTAINER="$(docker-compose ps | sed -n '3s/ .*//p')"
    echo "container is $DOCKER_CONTAINER"
    if [ -n "${NOTESTS:-}" ]; then
        exit 0
    fi
    non_solr_node1="127.0.0.1:1025"
    non_solr_node2="127.0.0.1:1026"
    hr
    SOLR_PORT="$SOLR_PORT_DEFAULT" ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_solrcloud.py $non_solr_node1 $non_solr_node2

    # shellcheck disable=SC2097,SC2098
    SOLR_PORT="$SOLR_PORT_DEFAULT" run_grep "^$SOLR_HOST:$SOLR_PORT$" ./find_active_solrcloud.py $non_solr_node1 $non_solr_node2 "$SOLR_HOST:$SOLR_PORT"

    docker-compose down
    hr
    echo
}

run_test_versions SolrCloud
