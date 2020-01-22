#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-05-25 01:38:24 +0100 (Mon, 25 May 2015)
#
#  https://github.com/harisekhon/devops-python-tools
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

# shellcheck disable=SC1091
. ./tests/utils.sh

section "E l a s t i c s e a r c h"

export ELASTICSEARCH_VERSIONS="${*:-${ELASTICSEARCH_VERSIONS:-latest 1.3 1.4 1.5 1.6 1.7 2.0 2.1 2.2 2.3 2.4 5.0 5.1 5.2 5.3 5.4 5.5 5.6 6.0.1 6.1.1}}"

ELASTICSEARCH_HOST="${DOCKER_HOST:-${ELASTICSEARCH_HOST:-${HOST:-localhost}}}"
ELASTICSEARCH_HOST="${ELASTICSEARCH_HOST##*/}"
ELASTICSEARCH_HOST="${ELASTICSEARCH_HOST%%:*}"
export ELASTICSEARCH_HOST
export ELASTICSEARCH_PORT_DEFAULT="${ELASTICSEARCH_PORT:-9200}"
export ELASTICSEARCH_INDEX="${ELASTICSEARCH_INDEX:-test}"

check_docker_available

trap_debug_env elasticsearch

# Elasticsearch 5.x takes ~ 50 secs to start up, sometimes doesn't start after 90 secs :-/
startupwait 120

test_elasticsearch(){
    local version="$1"
    section2 "Setting up Elasticsearch $version test container"
    if [ "$version" != "latest" ] && [ "${version:0:1}" -ge 6 ]; then
        export COMPOSE_FILE="$srcdir/docker/$DOCKER_SERVICE-elastic.co-docker-compose.yml"
    fi
    docker_compose_pull
    VERSION="$version" docker-compose up -d
    hr
    echo "getting Elasticsearch dynamic port mapping:"
    docker_compose_port "Elasticsearch"
    hr
    when_ports_available "$ELASTICSEARCH_HOST" "$ELASTICSEARCH_PORT"
    hr
    when_url_content "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT" "lucene_version"
    hr
    if [ -n "${NOTESTS:-}" ]; then
        exit 0
    fi
    non_es_node1="127.0.0.1:1025"
    non_es_node2="127.0.0.1:1026"
    ELASTICSEARCH_PORT="$ELASTICSEARCH_PORT_DEFAULT" \
    ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_elasticsearch.py $non_es_node1 $non_es_node2

    # shellcheck disable=SC2097,SC2098
    ELASTICSEARCH_PORT="$ELASTICSEARCH_PORT_DEFAULT" \
    run_grep "^$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT$" ./find_active_elasticsearch.py $non_es_node1 $non_es_node2 "$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT"

    docker-compose down
}

run_test_versions Elasticsearch
