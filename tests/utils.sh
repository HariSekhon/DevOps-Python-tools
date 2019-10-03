#!/usr/bin/env bash
# shellcheck disable=SC1090
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

set -eu
[ -n "${DEBUG:-}" ] && set -x
srcdir2="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

. "$srcdir2/excluded.sh"
. "$srcdir2/../bash-tools/lib/utils.sh"
. "$srcdir2/../bash-tools/lib/docker.sh"

srcdir="$srcdir2"

export COMPOSE_PROJECT_NAME="pytools"

if [ -n "${TRAVIS:-}" ]; then
    sudo=sudo
else
    # will be used in sourcing scripts
    # shellcheck disable=SC2034
    sudo=""
fi

set +o pipefail
spark_home="$(find . -type d -path 'tests/spark-*-bin-hadoop*' 2>/dev/null | head -n 1)"
set -o pipefail
if [ -n "$spark_home" ]; then
    export SPARK_HOME="$spark_home"
fi

. "$srcdir/excluded.sh"

. "$srcdir/check.sh"

# echo sample files except those with extensions given as args
sample_files(){
    local data_dir="$srcdir2/data"
    for filename in \
        "$data_dir/add_ou.ldif" \
        "$data_dir/multirecord.json" \
        "$data_dir/simple.xml" \
        "$data_dir/test.csv" \
        "$data_dir/test.ini" \
        "$data_dir/test.json" \
        "$data_dir/test.yaml" \
        "$data_dir/../../README.md" \
        ; do
        local excluded=0
        for ext in "$@"; do
            if [ "${filename##*.}" = "$ext" ]; then
                excluded=1
                break
            fi
        done
        if [ $excluded = 0 ]; then
            echo "$filename"
        fi
    done
}

check_broken_sample_files(){
    echo "Now checking non $* files to detect successful failure:"
    echo
    for filename in $(sample_files "$@"); do
        check_broken "$filename"
    done
}
