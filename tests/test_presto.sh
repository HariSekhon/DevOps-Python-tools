#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-09-22 17:01:38 +0200 (Fri, 22 Sep 2017)
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
srcdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$srcdir/..";

# shellcheck disable=SC1091
. ./tests/utils.sh

section "P r e s t o   S Q L"

export PRESTO_TERADATA_VERSIONS="latest 0.152 0.157 0.167 0.179"
export PRESTO_VERSIONS="${*:-${PRESTO_VERSIONS:-$PRESTO_TERADATA_VERSIONS}}"

PRESTO_HOST="${DOCKER_HOST:-${PRESTO_HOST:-${HOST:-localhost}}}"
PRESTO_HOST="${PRESTO_HOST##*/}"
PRESTO_HOST="${PRESTO_HOST%%:*}"
export PRESTO_HOST

export PRESTO_PORT_DEFAULT=8080
export PRESTO_PORT="${PRESTO_PORT:-$PRESTO_PORT_DEFAULT}"

check_docker_available

trap_debug_env presto

# recent Facebook releases e.g 0.187 can take a long time eg. 70 secs to fully start up
startupwait 90

test_presto2(){
    local version="$1"
    run_count=0
    if [ "$version" = "0.70" ]; then
        echo "Presto 0.70 does not start up due to bug 'java.lang.ClassCastException: org.slf4j.impl.JDK14LoggerAdapter cannot be cast to ch.qos.logback.classic.Logger', skipping..."
        return
    fi
    DOCKER_CONTAINER="${DOCKER_CONTAINER:-$DOCKER_CONTAINER}"
    section2 "Setting up Presto $version test container"
    docker_compose_pull
    # reset container as we start a presto worker inside later so we don't want to start successive workers on compounding failed runs
    [ -n "${KEEPDOCKER:-}" ] || VERSION="$version" docker-compose down || :
    VERSION="$version" docker-compose up -d
    echo "getting Presto dynamic port mapping:"
    docker_compose_port PRESTO "Presto Coordinator"
    hr
    when_ports_available "$PRESTO_HOST" "$PRESTO_PORT"
    hr
    # endpoint initializes blank, wait until there is some content, eg. nodeId
    # don't just run ./check_presto_state.py (this also doesn't work < 0.128)
    when_url_content "http://$PRESTO_HOST:$PRESTO_PORT/v1/service/presto/general" nodeId
    hr
    expected_version="$version"
    if [ "$version" = "latest" ] ||
       [ "$version" = "NODOCKER" ]; then
        if [ "$teradata_distribution" = 1 ]; then
            echo "latest version, fetching latest version from DockerHub master branch"
            expected_version="$(dockerhub_latest_version presto)"
        else
            # don't want to have to pull presto versions script from Dockerfiles repo
            expected_version=".*"
        fi
    fi
    echo "expecting Presto version '$expected_version'"
    hr

    non_presto_node1="127.0.0.1:1025"
    non_presto_node2="127.0.0.1:1026"
    hr
    PRESTO_PORT="$PRESTO_PORT_DEFAULT" ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_presto_coordinator.py $non_presto_node1 $non_presto_node2

    # shellcheck disable=SC2097,SC2098
    PRESTO_PORT="$PRESTO_PORT_DEFAULT" run_grep "^$PRESTO_HOST:$PRESTO_PORT$" ./find_active_presto_coordinator.py $non_presto_node1 "$PRESTO_HOST:$PRESTO_PORT"

    echo "Completed $run_count Presto tests"
    hr
    [ -z "${KEEPDOCKER:-}" ] || return 0
    [ -n "${NODOCKER:-}" ] ||
    docker-compose down
    hr
    echo
}

if [ -n "${NODOCKER:-}" ]; then
    PRESTO_VERSIONS="NODOCKER"
fi

test_presto(){
    local version="$1"
    local teradata_distribution=0
    local teradata_only=0
    local facebook_only=0
    if [[ "$version" =~ .*-teradata$ ]]; then
        version="${version%-teradata}"
        teradata_distribution=1
        teradata_only=1
    elif [[ "$version" =~ .*-facebook$ ]]; then
        version="${version%-facebook}"
        facebook_only=1
    else
        for teradata_version in $PRESTO_TERADATA_VERSIONS; do
            if [ "$version" = "$teradata_version" ]; then
                teradata_distribution=1
                break
            fi
        done
    fi
    if [ "$teradata_distribution" = "1" ] &&
       [ $facebook_only -eq 0 ]; then
        echo "Testing Teradata's Presto distribution version:  '$version'"
        COMPOSE_FILE="$srcdir/docker/presto-docker-compose.yml" test_presto2 "$version"
        # must call this manually here as we're sneaking in an extra batch of tests that run_test_versions is generally not aware of
        ((total_run_count+=run_count))
        # reset this so it can be used in test_presto to detect now testing Facebook
        teradata_distribution=0
    fi
    if [ -n "${NODOCKER:-}" ]; then
        echo "Testing External Presto:"
    else
        echo "Testing Facebook's Presto release version:  '$version'"
    fi
    if [ $teradata_only -eq 0 ]; then
        COMPOSE_FILE="$srcdir/docker/presto-dev-docker-compose.yml" test_presto2 "$version"
    fi
}

run_test_versions Presto
