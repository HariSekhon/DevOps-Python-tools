#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-05 23:29:15 +0000 (Thu, 05 Nov 2015)
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
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "
# ================== #
# Testing JSON Files
# ================== #
"

cd "$srcdir/..";

# shellcheck disable=SC1091
. ./tests/utils.sh

until [ $# -lt 1 ]; do
    case $1 in
        -*) shift || :
    esac
done

# ignore multi-line json data file for spark testing
for jsonFile in $(find "${1:-.}" -iname '*.json' |
                  grep -v -e '/spark-.*-bin-hadoop.*/' \
                          -e 'multirecord.json' \
                          -e 'broken' \
                          -e 'error'); do
    echo "testing json file: $jsonFile"
    python -mjson.tool < "$jsonFile" > /dev/null
done

echo
echo
