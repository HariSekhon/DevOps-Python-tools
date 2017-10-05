#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-05-25 01:38:24 +0100 (Mon, 25 May 2015)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/..";

. ./tests/utils.sh

section "E l a s t i c s e a r c h"

export ELASTICSEARCH_VERSIONS="${@:-${ELASTICSEARCH_VERSIONS:-latest 1.4 1.5 1.6 1.7 2.0 2.2 2.3 2.4 5.0}}"

ELASTICSEARCH_HOST="${DOCKER_HOST:-${ELASTICSEARCH_HOST:-${HOST:-localhost}}}"
ELASTICSEARCH_HOST="${ELASTICSEARCH_HOST##*/}"
ELASTICSEARCH_HOST="${ELASTICSEARCH_HOST%%:*}"
export ELASTICSEARCH_HOST
export ELASTICSEARCH_PORT_DEFAULT="${ELASTICSEARCH_PORT:-9200}"
export ELASTICSEARCH_INDEX="${ELASTICSEARCH_INDEX:-test}"

check_docker_available

trap_debug_env elasticsearch

startupwait 50

test_elasticsearch(){
    local version="$1"
    section2 "Setting up Elasticsearch $version test container"
    #launch_container "$DOCKER_IMAGE:$version" "$DOCKER_CONTAINER" $ELASTICSEARCH_PORT
    VERSION="$version" docker-compose up -d
    echo "getting Elasticsearch dynamic port mappings"
    printf "getting Elasticsearch HTTP port => "
    export ELASTICSEARCH_PORT="`docker-compose port "$DOCKER_SERVICE" "$ELASTICSEARCH_PORT_DEFAULT" | sed 's/.*://'`"
    echo "$ELASTICSEARCH_PORT"
    when_ports_available "$startupwait" "$ELASTICSEARCH_HOST" "$ELASTICSEARCH_PORT"
    hr
    when_url_content "$startupwait" "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT" "lucene_version"
    hr
    if [ -n "${NOTESTS:-}" ]; then
        exit 0
    fi
    non_es_node1="127.0.0.1:1025"
    non_es_node2="127.0.0.1:1026"
    hr
    ELASTICSEARCH_PORT="$ELASTICSEARCH_PORT_DEFAULT" check_output "NO_AVAILABLE_SERVER" ./find_active_elasticsearch_node.py $non_es_node1 $non_es_node2
    hr
    ELASTICSEARCH_PORT="$ELASTICSEARCH_PORT_DEFAULT" check_output "$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT" ./find_active_elasticsearch_node.py $non_es_node1 $non_es_node2 "$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT"
    hr
    #delete_container
    docker-compose down
}

run_test_versions Elasticsearch
