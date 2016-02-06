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
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
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
    cmd="$1"
    expected="$2"
    msg="$3"
    output="$(eval $cmd)"
    result="$(cksum <<< "$output")"
    echo -n "checking headtail $msg  =>  "
    if [ "$result" = "$expected" ]; then
        echo "success"
    else
        echo "FAILED, expected checksum '$expected', got checksum '$result'"
        echo
        echo "full output: "
        echo
        eval $cmd
        echo
        echo "cksum: $result"
        exit 1
    fi
}

check "./headtail.py $testfile" "789101572 545" "file"

check "cat $testfile | ./headtail.py -" "789101572 545" "-"

check "cat $testfile | ./headtail.py" "789101572 545" "noarg"

check "./headtail.py $testfile -n 20" "741605952 1024" "file -n 20"

check "cat $testfile | ./headtail.py - $testfile -n 20" "3412825758 2210" "mixed - file -n 20"

check "cat $testfile | ./headtail.py - $testfile - -n 20" "2618879084 2297" "mixed - file - -n 20"

echo
echo "======="
echo "SUCCESS"
echo "======="

echo
echo
