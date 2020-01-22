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

section "Testing validate_csv.py"

export TIMEOUT=3

if [ $# -gt 0 ]; then
    echo "validate_csv.py $*"
    ./validate_csv.py "$@"
    echo
fi

data_dir="tests/data"
broken_dir="tests/csv_broken"

exclude='/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+$|broken|error'

rm -fr "$broken_dir" || :
mkdir "$broken_dir"

./validate_csv.py --exclude "$exclude" .
echo

# ==================================================
hr2
echo
echo "checking directory recursion (mixed with explicit file given)"
./validate_csv.py "$data_dir/test.csv" "$data_dir"
echo

# ==================================================
hr2
echo "checking symlink handling"
ln -sfv "test.csv" "$data_dir/testlink.csv"
./validate_csv.py "$data_dir/testlink.csv"
rm "$data_dir/testlink.csv"
echo

# ==================================================
hr2
echo "checking csv file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.csv' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_csv.py -t 1 "$broken_dir/no_extension_testfile"
echo

# ==================================================
hr2
echo "testing stdin"
./validate_csv.py - < "$data_dir/test.csv"
./validate_csv.py < "$data_dir/test.csv"
echo "testing stdin mixed with filename"
# shellcheck disable=SC2094
./validate_csv.py "$data_dir/test.csv" - < "$data_dir/test.csv"
echo

#echo "testing print mode"
#[ "$(./validate_csv.py -p "$data_dir/test.csv" | cksum)" = "$(cksum < "$data_dir/test.csv")" ] || { echo "print test failed!"; exit 1; }
#echo "successfully passed out test csv to stdout"
#echo

# ==================================================
hr2
check_broken(){
    local filename="$1"
    local expected_exitcode="${2:-2}"
    local options="${*:3}"
    set +e
    # shellcheck disable=SC2086
    ./validate_csv.py -t 1 $options "$filename"
    exitcode=$?
    set -e
    if [ "$exitcode" = "$expected_exitcode" ]; then
        echo "successfully detected broken csv in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken csv in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken csv in '$filename'"
        exit 1
    fi
}

check_broken_sample_files csv

# ==================================================
hr2
echo "checking single word text file is not valid CSV"
echo blah > "$broken_dir/single_field.csv"
check_broken "$broken_dir/single_field.csv" 2

# ==================================================
hr2
echo "checking for non-existent file"
check_broken nonexistentfile 2

# ==================================================
hr2
echo "checking blank content is invalid"
echo > "$broken_dir/blank.csv"
check_broken "$broken_dir/blank.csv"

echo "checking blank content is invalid via stdin"
check_broken - 2 < "$broken_dir/blank.csv"

echo "checking blank content is invalid via stdin piped from /dev/null"
check_broken - 2 < /dev/null
echo

rm -fr "$broken_dir"

echo "======="
echo "SUCCESS"
echo "======="

echo
echo
