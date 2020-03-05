#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-26 23:36:03 +0000 (Tue, 26 Jan 2016)
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

srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/.."

# shellcheck disable=SC1090
. "$srcdir/utils.sh"

section "A p a c h e   D r i l l"

export APACHE_DRILL_VERSIONS="${*:-${APACHE_DRILL_VERSIONS:-0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.4 1.5 1.6 1.7 1.8 1.9 1.10 1.11 1.12 1.13 1.14 1.15 latest}}"

APACHE_DRILL_HOST="${DOCKER_HOST:-${APACHE_DRILL_HOST:-${HOST:-localhost}}}"
APACHE_DRILL_HOST="${APACHE_DRILL_HOST##*/}"
APACHE_DRILL_HOST="${APACHE_DRILL_HOST%%:*}"
export APACHE_DRILL_HOST
export APACHE_DRILL_PORT_DEFAULT=8047

check_docker_available

trap_debug_env apache_drill

test_apache_drill(){
    local version="$1"
    section2 "Setting up Apache Drill $version test container"
    docker_compose_pull
    VERSION="$version" docker-compose up -d
    hr
    echo "getting Apache Drill dynamic port mappings:"
    docker_compose_port "Apache Drill"
    hr
    # shellcheck disable=SC2153
    when_ports_available "$APACHE_DRILL_HOST" "$APACHE_DRILL_PORT"
    hr
    when_url_content "http://$APACHE_DRILL_HOST:$APACHE_DRILL_PORT/status" "Running"
    hr
    if [ -n "${NOTESTS:-}" ]; then
        exit 0
    fi
    docker_compose_version_test apache-drill "$version"
    hr

    non_drill_node1="127.0.0.1:1025"
    non_drill_node2="127.0.0.1:1026"
    hr
    APACHE_DRILL_PORT="$APACHE_DRILL_PORT_DEFAULT" ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_apache_drill.py $non_drill_node1 $non_drill_node2

    # shellcheck disable=SC2097,SC2098
    APACHE_DRILL_PORT="$APACHE_DRILL_PORT_DEFAULT" run_grep "^$APACHE_DRILL_HOST:$APACHE_DRILL_PORT$" ./find_active_apache_drill.py $non_drill_node1 "$APACHE_DRILL_HOST:$APACHE_DRILL_PORT"

    # Drill 1.7+ only
    if [ "$version" = "latest" ] || [ "$(bc <<< "$version > 1.6")" = 1 ]; then
        APACHE_DRILL_PORT="$APACHE_DRILL_PORT_DEFAULT" ERRCODE=1 run_grep "^NO_AVAILABLE_SERVER$" ./find_active_apache_drill2.py $non_drill_node1 $non_drill_node2

        # shellcheck disable=SC2097,SC2098
        APACHE_DRILL_PORT="$APACHE_DRILL_PORT_DEFAULT" run_grep "^$APACHE_DRILL_HOST:$APACHE_DRILL_PORT$" ./find_active_apache_drill2.py $non_drill_node1 "$APACHE_DRILL_HOST:$APACHE_DRILL_PORT"
    fi

    # run_count defined in util lib
    # shellcheck disable=SC2154
    echo "Completed $run_count Apache Drill tests"
    hr
    [ -n "${KEEPDOCKER:-}" ] ||
    docker-compose down
    echo
}

startupwait 120

run_test_versions "Apache Drill"
