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
[ -n "${TRAVIS:-}" ] && set -x
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

data_dir="tests/data"
broken_dir="$data_dir/broken_json_data"

rm -fr "$broken_dir" || :
mkdir "$broken_dir"
./validate_json.py -vvv $(
find "${1:-.}" -iname '*.json' |
grep -v '/spark-.*-bin-hadoop.*/' |
grep -v -e 'broken' -e 'error' -e ' '
)
echo
echo "checking directory recursion (mixed with explicit file given)"
./validate_json.py -vvv "$data_dir/test.json" .
echo

echo "checking json file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.json' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_json.py -vvv -t 1 "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_json.py - < "$data_dir/test.json"
./validate_json.py < "$data_dir/test.json"
echo "testing stdin and file mix"
./validate_json.py "$data_dir/test.json" - < "$data_dir/test.json"
echo "testing stdin with multi-record"
./validate_json.py -m - < "$data_dir/multirecord.json"
echo

echo "checking symlink handling"
ln -sfv "test.json" "$data_dir/testlink.json"
./validate_json.py "$data_dir/testlink.json"
rm "$data_dir/testlink.json"
echo

echo "Now trying broken / non-json files to test failure detection:"
check_broken(){
    filename="$1"
    expected_exitcode="${2:-2}"
    set +e
    ./validate_json.py "$filename" ${@:3}
    exitcode=$?
    set -e
    if [ $exitcode = $expected_exitcode ]; then
        echo "successfully detected broken json in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken json in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken json in '$filename'"
        exit 1
    fi
}

echo "checking normal json file breakage using --multi-record switch"
set +e
./validate_json.py - -m < "$data_dir/test.json"
exitcode=$?
set -e
if [ $exitcode = 2 ]; then
    echo "successfully detected breakage for --multi-line stdin vs normal json"
    echo
else
    echo "FAILED to detect breakage when feeding normal multi-line json doc to stdin with --multi-line (expecting one json doc per line), returned unexpected exit code $exitcode"
    exit 1
fi

echo blah > "$broken_dir/blah.json"
check_broken "$broken_dir/blah.json"

echo "{ 'name': 'hari' }" > "$broken_dir/single_quote.json"
check_broken "$broken_dir/single_quote.json"

echo "checking specifically single quote detection"
set +o pipefail
./validate_json.py "$broken_dir/single_quote.json" 2>&1 | grep --color 'JSON INVALID.*found single quotes not double quotes' || { echo "Failed to find single quote message in output"; exit 1; }
set -o pipefail
echo

# TODO: add failure print silent mode exit code and stdout/stderr
echo "testing print mode"
[ "$(./validate_json.py -p "$data_dir/test.json" | cksum)" = "$(cksum < "$data_dir/test.json")" ] || { echo "print test failed!"; exit 1; }
echo "successfully passed out test json to stdout"
echo "testing print mode with multi-record"
[ "$(./validate_json.py -mp "$data_dir/multirecord.json" | cksum)" = "$(cksum < "$data_dir/multirecord.json")" ] || { echo "print multi-record test failed!"; exit 1; }
echo "successfully passed out multi-record json to stdout"
echo

echo '{ "name": "hari" ' > "$broken_dir/missing_end_quote.json"
check_broken "$broken_dir/missing_end_quote.json"

check_broken README.md

cat "$data_dir/test.json" >> "$broken_dir/multi-broken.json"
cat "$data_dir/test.json" >> "$broken_dir/multi-broken.json"
check_broken "$broken_dir/multi-broken.json"
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
