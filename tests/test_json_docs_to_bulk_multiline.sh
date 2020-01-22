#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2017-07-30 14:30:00 +0200 (Sun, 30 Jul 2017)
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

section "Testing json_docs_to_bulk_multiline.py"

until [ $# -lt 1 ]; do
    case $1 in
        -*) shift || :
    esac
done

stdout="/dev/null"
stderr="/dev/null"
if [ "${DEBUG:-}" ]; then
    stdout="/dev/stdout"
    stderr="/dev/stderr"
fi

data_dir="tests/data"
broken_dir="$data_dir/broken_json_data"

exclude='/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+$|broken|error'

rm -fr "$broken_dir" || :
mkdir "$broken_dir"

./json_docs_to_bulk_multiline.py --exclude "$exclude" . >/dev/null
echo

# ==================================================
hr2
echo "checking directory recursion (mixed with explicit file given)"
./json_docs_to_bulk_multiline.py "$data_dir/test.json" "$data_dir" > "$stdout"
echo

# ==================================================
hr2
echo "checking json file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.json' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./json_docs_to_bulk_multiline.py -t 1 "$broken_dir/no_extension_testfile" > "$stdout"
echo

# ==================================================
hr2
echo "checking json with embedded double quotes"
./json_docs_to_bulk_multiline.py "$data_dir/embedded_double_quotes.json" > "$stdout"
echo

# ==================================================
hr2
echo "checking multirecord json with blank lines"
./json_docs_to_bulk_multiline.py "$data_dir/multirecord_with_blank_lines.notjson" > "$stdout"
echo

# ==================================================
hr2
echo "testing regular json doc"
./json_docs_to_bulk_multiline.py "$data_dir/test.json" > "$stdout"
echo "testing multiline json doc "
./json_docs_to_bulk_multiline.py "$data_dir/multirecord.json" > "$stdout"

# ==================================================
hr2
echo "testing stdin"
./json_docs_to_bulk_multiline.py - < "$data_dir/test.json" > "$stdout"
./json_docs_to_bulk_multiline.py < "$data_dir/test.json" > "$stdout"
echo "testing stdin and file mix"
# shellcheck disable=SC2094
./json_docs_to_bulk_multiline.py "$data_dir/test.json" - < "$data_dir/test.json" > "$stdout"

# ==================================================
hr2
echo "checking symlink handling"
ln -sfv "test.json" "$data_dir/testlink.json"
./json_docs_to_bulk_multiline.py "$data_dir/testlink.json" > "$stdout"
rm "$data_dir/testlink.json"
echo

# ==================================================
hr2
echo "Now trying broken / non-json files to test failure detection:"
check_broken(){
    filename="$1"
    expected_exitcode="${2:-2}"
    set +e
    # shellcheck disable=SC2086
    ./json_docs_to_bulk_multiline.py "$filename" ${*:3} 2> "$stderr" > "$stdout"
    exitcode=$?
    set -e
    if [ $exitcode = "$expected_exitcode" ]; then
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

# ==================================================
hr2
echo blah > "$broken_dir/blah.json"
check_broken "$broken_dir/blah.json"
check_broken "$data_dir/single_quotes.notjson"
check_broken "$data_dir/single_quotes_embedded_double_quotes.notjson"
check_broken "$data_dir/single_quotes_embedded_double_quotes_unescaped.notjson"

# ==================================================
hr2
echo "testing stdin breaks on multi-record"
check_broken - < "$data_dir/multirecord.json" 2
echo

# ==================================================
hr2
echo "checking invalid single quote detection"
# Alpine's busybox grep doesn't have color
if grep --help 2>&1 | grep -q -- --color; then
    grep_opts="--color"
else
    grep_opts="-o"
fi
set +o pipefail
./json_docs_to_bulk_multiline.py -vvv "$data_dir/single_quotes.notjson" 2>&1 |
    tee "$stderr" |
        grep $grep_opts -- ' - ERROR - invalid json detected in ' ||
            { echo "Failed to find single quote message in output"; exit 1; }
set -o pipefail
echo

# ==================================================
hr2
echo "checking --permit-single-quotes mode works"
./json_docs_to_bulk_multiline.py -s "$data_dir/single_quotes.notjson" > "$stdout"
echo

echo "checking --permit-single-quotes mode works with embedded double quotes"
./json_docs_to_bulk_multiline.py -s "$data_dir/single_quotes_embedded_double_quotes.notjson" > "$stdout"
echo

echo "checking --permit-single-quotes mode works with single quotes with ununescaped embedded double quotes"
./json_docs_to_bulk_multiline.py -s "$data_dir/single_quotes_embedded_double_quotes_unescaped.notjson" > "$stdout"
echo

# ==================================================
hr2
echo "checking --permit-single-quotes mode works with multirecord"
./json_docs_to_bulk_multiline.py -s "$data_dir/multirecord_single_quotes.notjson" > "$stdout"
echo

echo "checking --permit-single-quotes mode works with multirecord single quotes with embedded double quotes"
./json_docs_to_bulk_multiline.py -s "$data_dir/multirecord_single_quotes_embedded_double_quotes.notjson" > "$stdout"
echo

echo "checking --permit-single-quotes mode works with multirecord single quotes with unescaped embedded double quotes"
./json_docs_to_bulk_multiline.py -s "$data_dir/multirecord_single_quotes_embedded_double_quotes_unescaped.notjson" > "$stdout"
echo

# ==================================================
hr2
echo "testing output contents"
[ "$(./json_docs_to_bulk_multiline.py "$data_dir/test.json" | cksum)" = "3304080878 35" ] ||
    { echo "print test failed!"; exit 1; }
echo "successfully passed out test json to stdout"
echo
echo "testing print mode with multi-record"
[ "$(./json_docs_to_bulk_multiline.py "$data_dir/multirecord.json" | cksum)" = "3835865587 35" ] ||
    { echo "print multi-record test failed!"; exit 1; }
echo "successfully passed out multi-record json to stdout"
echo
echo "testing print mode with --permit-single-quotes"
[ "$(./json_docs_to_bulk_multiline.py -s "$broken_dir/single_quotes.json" | cksum)" = "2117996339 59" ] ||
    { echo "print single quote json test failed!"; exit 1; }
echo

# ==================================================
hr2
echo '{ "name": "hari" ' > "$broken_dir/missing_end_quote.json"
check_broken "$broken_dir/missing_end_quote.json"

check_broken README.md 2> /dev/null

cat "$data_dir/test.json" >> "$broken_dir/multi-broken.json"
cat "$data_dir/test.json" >> "$broken_dir/multi-broken.json"
check_broken "$broken_dir/multi-broken.json" 2> "$stderr"
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
