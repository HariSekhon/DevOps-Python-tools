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

set -eu
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/..";

# shellcheck disable=SC1091
. ./tests/utils.sh

while read -r prog; do
    isExcluded "$prog" && continue
    if type -P flake8 &> /dev/null; then
        echo "flake8 $prog"
        flake8 --max-line-length=120 --statistics "$prog"
        echo; hr; echo
    fi
    for y in pyflakes pychecker; do
        if type -P "$y" &>/dev/null; then
            echo "$y $prog"
            "$y" "$prog"
            echo; hr; echo
        fi
   done
done < <(find . -type f -name '*.py' -o -type f -name '*.jy')
