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
#  http://www.linkedin.com/in/harisekhon
#

set -eu
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/..";

. ./tests/utils.sh

for x in $(echo *.py 2>/dev/null); do
    isExcluded "$x" && continue
    set +e
    echo ./$x --help
    ./$x --help # >/dev/null
    status=$?
    set -e
    [ $status = 3 -o $status = 0 ] || { echo "status code for $x --help was $status not expected 0 or 3"; exit 1; }
done
echo "All Python programs found exited with expected code 0/3 for --help"
