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
# Testing headtail.py
# ======================== #
"

cd "$srcdir/..";

. ./tests/utils.sh

until [ $# -lt 1 ]; do
    case $1 in
        -*) shift
    esac
done

data_dir="tests/data"
broken_dir="$data_dir/broken_json_data"

testfile="$data_dir/plant_catalog.xml"

check(){
    result="$1"
    expected="$2"
    msg="$3"
    echo -n "checking headtail $msg  =>  "
    if [ "$result" = "$expected" ]; then
        echo "success"
    else
        echo "FAILED, expected '$expected', got '$result'"
        exit 1
    fi
}

check "$(./headtail.py "$testfile" | cksum)" "1228592176 939" "file"

check "$(cat "$testfile" | ./headtail.py - | cksum)" "1228592176 939" "-"

check "$(cat "$testfile" | ./headtail.py | cksum)" "1228592176 939" "noarg"

check "$(./headtail.py "$testfile" -n 20 | cksum)" "2465317856 1705" "file -n 20"

check "$(cat "$testfile" | ./headtail.py - "$testfile" -n 20 | cksum)" "1730569196 3410" "mixed - file -n 20"

check "$(cat "$testfile" | ./headtail.py - "$testfile" - -n 20 | cksum)" "110081398 3438" "mixed - file - -n 20"

echo
echo "======="
echo "SUCCESS"
echo "======="

echo
echo
