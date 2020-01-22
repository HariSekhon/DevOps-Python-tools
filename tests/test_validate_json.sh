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

section "Testing validate_json.py"

export TIMEOUT=${TIMEOUT:-3}

if [ $# -gt 0 ]; then
    echo "validate_json.py $*"
    ./validate_json.py "$@"
    echo
fi

data_dir="tests/data"
broken_dir="$data_dir/broken_json_data"

exclude='/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+$|broken|error'

rm -fr "$broken_dir" || :
mkdir "$broken_dir"

echo "checking all JSON files in local directory"
./validate_json.py --exclude "$exclude" .
echo

# ==================================================
hr2
echo "checking multirecord json"
./validate_json.py "$data_dir/multirecord.json"
echo

# ==================================================
hr2
echo "checking directory recursion (mixed with explicit file given)"
./validate_json.py "$data_dir/test.json" .
echo

# ==================================================
hr2
echo "checking json file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.json' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_json.py -t 1 "$broken_dir/no_extension_testfile"
echo

# ==================================================
hr2
echo "testing stdin"
./validate_json.py - < "$data_dir/test.json"
./validate_json.py < "$data_dir/test.json"
echo "testing stdin and file mix"
# shellcheck disable=SC2094
./validate_json.py "$data_dir/test.json" - < "$data_dir/test.json"
echo "testing stdin with multirecord"
./validate_json.py -m - < "$data_dir/multirecord.json"
echo

# ==================================================
hr2
echo "checking symlink handling"
ln -sfv "test.json" "$data_dir/testlink.json"
./validate_json.py "$data_dir/testlink.json"
rm "$data_dir/testlink.json"
echo

check_broken(){
    local filename="$1"
    local expected_exitcode="${2:-2}"
    local options="${*:3}"
    set +e
    # shellcheck disable=SC2086
    ./validate_json.py $options "$filename"
    exitcode=$?
    set -e
    if [ "$exitcode" = "$expected_exitcode" ]; then
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
echo "checking normal json stdin breakage using --multi-record switch"
set +e
./validate_json.py - -m < "$data_dir/test.json"
exitcode=$?
set -e
if [ $exitcode = 2 ]; then
    echo "successfully detected breakage for --multi-record stdin vs normal json"
    echo
else
    echo "FAILED to detect breakage when feeding normal json doc to stdin with --multi-record (expecting one json doc per line), returned unexpected exit code $exitcode"
    exit 1
fi

echo "checking multirecord json stdin breakage without using --multi-record switch"
set +e
./validate_json.py - < "$data_dir/multirecord.json"
exitcode=$?
set -e
if [ $exitcode = 2 ]; then
    echo "successfully detected breakage for multirecord json on stdin without using --multi-record switch"
    echo
else
    echo "FAILED to detect breakage when feeding multirecord json to stdin without using --multi-record, returned unexpected exit code $exitcode"
    exit 1
fi

# ==================================================
hr2
echo blah > "$broken_dir/blah.json"
check_broken "$broken_dir/blah.json"

check_broken "$data_dir/single_quotes.notjson"
check_broken "$data_dir/multirecord_single_quotes.notjson"
check_broken "$data_dir/multirecord_single_quotes_embedded_double_quotes.notjson"
check_broken "$data_dir/multirecord_single_quotes_embedded_double_quotes_unescaped.notjson"

# ==================================================
hr2
# TODO: make this check pass again - the problem is it'll be more expensive to run this check just to give better feedback to the user
#echo "checking invalid single quote detection"
# # Alpine's busybox grep doesn't have color
# if grep --help 2>&1 | grep -q -- --color; then
#     grep_opts="--color"
# else
#     grep_opts="-o"
# fi
#set +o pipefail
#./validate_json.py "$data_dir/single_quotes.notjson" 2>&1 |
#   tee /dev/stderr |
#       grep $grep_opts 'JSON INVALID.*single quotes detected' ||
#           { echo "Failed to find single quote message in output"; exit 1; }
#set -o pipefail
#echo

echo "checking --permit-single-quotes mode works"
./validate_json.py -s "$data_dir/single_quotes.notjson"
echo

echo "checking --permit-single-quotes mode works with embedded double quotes"
./validate_json.py -s "$data_dir/single_quotes_embedded_double_quotes.notjson"
echo

echo "checking --permit-single-quotes mode works with unescaped embedded double quotes"
./validate_json.py -s "$data_dir/single_quotes_embedded_double_quotes_unescaped.notjson"
echo

# ==================================================
hr2
echo "checking --permit-single-quotes mode works with multirecord single quoted json"
./validate_json.py -s "$data_dir/multirecord_single_quotes.notjson" -m
echo

echo "checking --permit-single-quotes mode infers multirecord single quoted json"
./validate_json.py -s "$data_dir/multirecord_single_quotes.notjson"
echo

# ==================================================
hr2
echo "checking --permit-single-quotes mode works with multirecord single quoted json with embedded double quotes"
./validate_json.py -s "$data_dir/multirecord_single_quotes_embedded_double_quotes.notjson" -m
echo

echo "checking --permit-single-quotes mode infers multirecord single quoted json with embedded double quotes"
./validate_json.py -s "$data_dir/multirecord_single_quotes_embedded_double_quotes.notjson"
echo

# ==================================================
hr2
echo "checking --permit-single-quotes mode works with multirecord json with unescaped embedded double quotes"
./validate_json.py -s "$data_dir/multirecord_single_quotes_embedded_double_quotes_unescaped.notjson" -m
echo

echo "checking --permit-single-quotes mode infers multirecord single quoted json with unescaped embedded double quotes"
./validate_json.py -s "$data_dir/multirecord_single_quotes_embedded_double_quotes_unescaped.notjson"
echo

# ==================================================
hr2
echo "checking --permit-single-quotes mode works with multirecord single quoted json with mixed quoting"
./validate_json.py -s "$data_dir/multirecord_single_double_mixed_quotes.notjson" -m
echo

echo "checking --permit-single-quotes mode infers multirecord single quoted json with mixed quoting"
./validate_json.py -s "$data_dir/multirecord_single_double_mixed_quotes.notjson"
echo

echo "checking --permit-single-quotes mode works with multirecord single quoted json with mixed quoting (should result in a WARNING message)"
if ./validate_json.py -s "$data_dir/multirecord_single_double_mixed_quotes.notjson" -m 2>&1 | grep -q WARNING; then
    echo "Found warning message"
else
    echo "failed to raise a WARNING message for mixed quoting"
    exit 1
fi
echo

echo "checking --permit-single-quotes mode infers multirecord single quoted json with mixed quoting (should result in a WARNING message)"
if ./validate_json.py -s "$data_dir/multirecord_single_double_mixed_quotes.notjson" 2>&1 | grep -q WARNING; then
    echo "Found warning message"
else
    echo "failed to raise a WARNING message while inferring mixed quoting"
    exit 1
fi
echo

# ============================================================================ #
#                          Print Mode Passthrough Tests
# ============================================================================ #
hr2
echo "# Print Mode Passthrough Tests"
hr2

echo "testing print mode"
[ "$(./validate_json.py -p "$data_dir/test.json" | cksum)" = "$(cksum < "$data_dir/test.json")" ] || { echo "print test failed!"; exit 1; }
echo "successfully passed test json to stdout"
echo

echo "testing print mode failed"
set +e
output="$(./validate_json.py -p "$data_dir/single_quotes.notjson")"
result=$?
set -e
[ $result -eq 2 ] || { echo "print test failed with wrong exit code $result instead of 2!"; exit 1; }
[ -z "$output" ] || { echo "print test failed by passing output to stdout for records that should be broken!"; exit 1; }
echo "successfully passed test of print mode failure"
echo

echo "testing print mode with multirecord"
[ "$(./validate_json.py -mp "$data_dir/multirecord.json" | cksum)" = "$(cksum < "$data_dir/multirecord.json")" ] ||
    { echo "print multirecord test failed!"; exit 1; }
echo "successfully passed multirecord json to stdout"
echo

echo "testing print mode with --permit-single-quotes"
[ "$(./validate_json.py -sp "$data_dir/single_quotes.notjson" | cksum)" = "$(cksum < "$data_dir/single_quotes.notjson")" ] ||
    { echo "print single quote json test failed!"; exit 1; }
echo "successfully passed single quoted json to stdout"
echo

echo "testing print mode with --permit-single-quotes multirecord"
[ "$(./validate_json.py -sp "$data_dir/multirecord_single_quotes.notjson" | cksum)" = "$(cksum < "$data_dir/multirecord_single_quotes.notjson")" ] ||
    { echo "print single quote multirecord singled quoted json test failed!"; exit 1; }
echo "successfully passed multirecord single quoted json stdout test"
echo

echo "testing print mode with --permit-single-quotes multirecord with embedded double quotes"
[ "$(./validate_json.py -sp "$data_dir/multirecord_single_quotes_embedded_double_quotes.notjson" | cksum)" = "$(cksum < "$data_dir/multirecord_single_quotes_embedded_double_quotes.notjson")" ] ||
    { echo "print single quote multirecord json with embedded double quotes test failed!"; exit 1; }
echo "successfully passed multirecord single quoted with embedded double quotes to stdout"
echo

echo "testing print mode with --permit-single-quotes multirecord with unescaped embedded double quotes"
[ "$(./validate_json.py -sp "$data_dir/multirecord_single_quotes_embedded_double_quotes_unescaped.notjson" | cksum)" = "$(cksum < "$data_dir/multirecord_single_quotes_embedded_double_quotes_unescaped.notjson")" ] ||
    { echo "print single quote multirecord json with unescaped embedded double quotes test failed!"; exit 1; }
echo "successfully passed multirecord single quoted with embedded unescaped double quotes to stdout"
echo

echo
# ============================================================================ #
hr2

echo '{ "name": "hari" ' > "$broken_dir/missing_end_quote.json"
check_broken "$broken_dir/missing_end_quote.json"

check_broken README.md

cat "$data_dir/test.json" >> "$broken_dir/multi-broken.json"
cat "$data_dir/test.json" >> "$broken_dir/multi-broken.json"
check_broken "$broken_dir/multi-broken.json"
echo

echo "checking for non-existent file"
check_broken nonexistentfile 2
echo

# ==================================================
hr2
echo "checking blank content is invalid"
echo > "$broken_dir/blank.json"
check_broken "$broken_dir/blank.json"

echo "checking blank content is invalid for multirecord"
check_broken "$broken_dir/blank.json" 2 -m

echo "checking blank content is invalid via stdin"
check_broken - 2 < "$broken_dir/blank.json"

echo "checking blank content is invalid for multirecord via stdin"
check_broken - 2 -m < "$broken_dir/blank.json"

echo "checking blank content is invalid for multirecord via stdin piped from /dev/null"
check_broken - 2 -m < /dev/null
echo

check_broken_sample_files json

rm -fr "$broken_dir"

echo "======="
echo "SUCCESS"
echo "======="

echo
echo
