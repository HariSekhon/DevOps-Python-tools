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
# Testing validate_csv.py
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
broken_dir="tests/csv_broken"

rm -fr "$broken_dir" || :
mkdir "$broken_dir"
./validate_csv.py -vvv $(
find "${1:-.}" -iname '*.csv' |
grep -v '/spark-.*-bin-hadoop.*/' |
grep -v -e 'broken' -e 'error' -e ' '
)
echo

echo
echo "checking directory recursion (mixed with explicit file given)"
./validate_csv.py -vvv "$data_dir/test.csv" "$data_dir"
echo

echo "checking symlink handling"
ln -sfv "test.csv" "$data_dir/testlink.csv"
./validate_csv.py "$data_dir/testlink.csv"
rm "$data_dir/testlink.csv"
echo

echo "checking csv file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.csv' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_csv.py -vvv -t 1 "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_csv.py - < "$data_dir/test.csv"
./validate_csv.py < "$data_dir/test.csv"
echo "testing stdin mixed with filename"
./validate_csv.py "$data_dir/test.csv" - < "$data_dir/test.csv"
echo

#echo "testing print mode"
#[ "$(./validate_csv.py -p "$data_dir/test.csv" | cksum)" = "$(cksum < "$data_dir/test.csv")" ] || { echo "print test failed!"; exit 1; }
#echo "successfully passed out test csv to stdout"
#echo

echo "Now trying non-csv files to detect successful failure:"
check_broken(){
    filename="$1"
    expected_exitcode="${2:-2}"
    set +e
    ./validate_csv.py -vvv -t 1 "$filename" ${@:3}
    exitcode=$?
    set -e
    if [ $exitcode = $expected_exitcode ]; then
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
check_broken "$data_dir/test.json"
check_broken "$data_dir/test.yaml"
check_broken "$data_dir/simple.xml"
check_broken "$data_dir/multirecord.json"
check_broken README.md
rm -fr "$broken_dir"
echo

echo "checking for non-existent file"
check_broken nonexistentfile 1
echo

echo "======="
echo "SUCCESS"
echo "======="

echo
echo
