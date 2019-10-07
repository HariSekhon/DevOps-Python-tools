#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-12-22 23:39:33 +0000 (Tue, 22 Dec 2015)
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

section "Testing validate_cson.py"

export TIMEOUT=3

exclude='/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+$|broken|error'

data_dir="tests/data"
broken_dir="tests/cson_broken"

if [ $# -gt 0 ]; then
    echo "validate_cson.py $*"
    ./validate_cson.py "$@"
    echo
fi

data_dir="tests/data"
if is_inside_docker; then
    export TIMEOUT=120
fi

rm -fr "$broken_dir" || :
mkdir "$broken_dir"

./validate_cson.py --exclude "$exclude" .
echo

echo
echo "checking directory recursion (mixed with explicit file given)"
./validate_cson.py "$data_dir/test.json"
echo

echo "checking symlink handling"
ln -sfv "test.json" "$data_dir/testlink.json"
./validate_cson.py "$data_dir/testlink.json"
rm "$data_dir/testlink.json"
echo

echo "checking cson file without an extension"
cp -iv "$(find "${1:-.}" -type f -iname '*.json' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_cson.py -t 1 "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_cson.py - < "$data_dir/test.json"
./validate_cson.py < "$data_dir/test.json"
echo "testing stdin mixed with filename"
# shellcheck disable=SC2094
./validate_cson.py "$data_dir/test.json" - < "$data_dir/test.json"
echo

check_broken(){
    local filename="$1"
    local expected_exitcode="${2:-2}"
    local options="${*:3}"
    set +e
    # shellcheck disable=SC2086
    ./validate_cson.py -t 1 $options "$filename"
    exitcode=$?
    set -e
    if [ "$exitcode" = "$expected_exitcode" ]; then
        echo "successfully detected broken cson in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken cson in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken cson in '$filename'"
        exit 1
    fi
}

check_broken_sample_files json cson

rm -fr "$broken_dir"

echo

echo "checking for non-existent file"
check_broken nonexistentfile 2
echo

echo "======="
echo "SUCCESS"
echo "======="

echo
echo
