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
# Testing validate_avro.py
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
broken_dir="tests/avro_broken"
# this relies on being run after the Spark => Avro tests to generate these files as I don't store avro files in this repo
rm -f "$data_dir/test.avro"
cp -v "$(find . -type f -iname '*.avro' | head -n1)" "$data_dir/test.avro"

rm -fr "$broken_dir" || :
mkdir "$broken_dir"
./validate_avro.py -vvv $(
find "${1:-.}" -type f -iname '*.avro' |
grep -v '/spark-.*-bin-hadoop.*/' |
grep -v -e 'broken' -e 'error' -e ' '
)
echo

echo
echo "checking directory recursion (mixed with explicit file given)"
./validate_avro.py -vvv "$data_dir/test.avro" .
echo

echo "checking symlink handling"
ln -sfv "test.avro" "$data_dir/testlink.avro"
./validate_avro.py "$data_dir/testlink.avro"
rm "$data_dir/testlink.avro"
echo

echo "checking avro file without an extension"
cp -iv "$(find "${1:-.}" -type f -iname '*.avro' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_avro.py -vvv -t 1 "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_avro.py - < "$data_dir/test.avro"
./validate_avro.py < "$data_dir/test.avro"
echo "testing stdin mixed with filename"
./validate_avro.py "$data_dir/test.avro" - < "$data_dir/test.avro"
echo

echo "Now trying non-avro files to detect successful failure:"
check_broken(){
    filename="$1"
    expected_exitcode="${2:-2}"
    set +e
    ./validate_avro.py -vvv -t 1 "$filename" ${@:3}
    exitcode=$?
    set -e
    if [ $exitcode = $expected_exitcode ]; then
        echo "successfully detected broken avro in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken avro in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken avro in '$filename'"
        exit 1
    fi
}
check_broken "$data_dir/multirecord.json"
rm -fr "$broken_dir"
echo

echo "checking for non-existent file"
check_broken nonexistentfile 1
echo

rm -v "$data_dir/test.avro"

echo "======="
echo "SUCCESS"
echo "======="

echo
echo
