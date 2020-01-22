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

section "Testing validate_parquet.py"

if [ -n "${SKIP_PARQUET:-}" ]; then
    echo "Skipping Parquet checks..."
    exit 0
fi

# validating parquet is relatively slow
#export TIMEOUT=10

if [ $# -gt 0 ]; then
    echo "validate_parquet.py $*"
    ./validate_parquet.py "$@"
    echo
fi

data_dir="tests/data"
broken_dir="tests/parquet_broken"
# this relies on being run after the Spark => parquet tests to generate these files as I don't store parquet files in this repo
rm -f "$data_dir/test.parquet"
# find will exit non-zero due to broken pipe caused by head
set +o pipefail
sample_parquet_file="$(find . -type f -iname '*.parquet' | head -n1)"
set -o pipefail
if [ -z "$sample_parquet_file" ] && is_inside_docker; then
    echo "No sample parquet file found and running inside docker, skipping validate_parquet.py tests"
    exit 0
fi
cp -v "$sample_parquet_file" "$data_dir/test.parquet"

exclude='/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+$|broken|error'

if is_inside_docker; then
    export TIMEOUT=200
    export EXCLUDE="$exclude"
fi

rm -fr "$broken_dir" || :
mkdir "$broken_dir"

./validate_parquet.py -vvv --exclude "$exclude" .
echo

echo
echo "checking directory recursion (mixed with explicit file given)"
./validate_parquet.py -vvv "$data_dir/test.parquet" . -t 120
echo

echo "checking symlink handling"
ln -sfv "test.parquet" "$data_dir/testlink.parquet"
./validate_parquet.py "$data_dir/testlink.parquet"
rm "$data_dir/testlink.parquet"
echo

echo "checking parquet file without an extension"
cp -iv "$(find "${1:-.}" -type f -iname '*.parquet' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_parquet.py -vvv -t 5 "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_parquet.py - < "$data_dir/test.parquet"
./validate_parquet.py < "$data_dir/test.parquet"
echo "testing stdin mixed with filename"
# shellcheck disable=SC2094
./validate_parquet.py "$data_dir/test.parquet" - < "$data_dir/test.parquet"
echo

check_broken(){
    local filename="$1"
    local expected_exitcode="${2:-2}"
    local options="${*:3}"
    set +e
    # shellcheck disable=SC2086
    ./validate_parquet.py -t 5 $options "$filename"
    exitcode=$?
    set -e
    if [ "$exitcode" = "$expected_exitcode" ]; then
        echo "successfully detected broken parquet in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken parquet in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken parquet in '$filename'"
        exit 1
    fi
}


check_broken_sample_files parquet

rm -fr "$broken_dir"

echo

echo "checking for non-existent file"
check_broken nonexistentfile 2
echo

rm -v "$data_dir/test.parquet"

echo "======="
echo "SUCCESS"
echo "======="

echo
echo
