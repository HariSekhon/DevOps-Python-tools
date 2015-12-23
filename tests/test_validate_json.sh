#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-12-22 23:39:33 +0000 (Tue, 22 Dec 2015)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  http://www.linkedin.com/in/harisekhon
#

set -euo pipefail
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "
# ======================== #
# Testing validate_json.py
# ======================== #
"

cd "$srcdir/..";

. ./tests/utils.sh

until [ $# -lt 1 ]; do
    case $1 in
        -*) shift
    esac
done

rm broken.json &>/dev/null || :
./validate_json.py -vvv $(
find "${1:-.}" -iname '*.json' |
grep -v '/spark-.*-bin-hadoop.*/'
)

echo "Now trying non-json files to detect successful failure:"
check_broken(){
    f="$1"
    set +e
    ./validate_json.py "$f"
    result=$?
    set -e
    if [ $result = 2 ]; then
        echo "successfully detected broken json in '$f', returned exit code $result"
    #elif [ $result != 0 ]; then
    #    echo "returned unexpected non-zero exit code $result for broken json in '$f'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $result for broken json in '$f'"
        exit 1
    fi
}
echo blah > broken.json
check_broken broken.json
rm broken.json
check_broken README.md
echo "======="
echo "SUCCESS"
echo "======="

echo
echo
