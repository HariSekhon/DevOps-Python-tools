#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-01-29 21:45:49 +0000 (Fri, 29 Jan 2016)
#
#  https://github.com/harisekhon
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback
#
#  https://www.linkedin.com/in/harisekhon
#

# Quick tests, need to replace with testcmd.exp

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/.."

# shellcheck disable=SC1091
. "bash-tools/lib/utils.sh"

section "Testing center.py"


expected="                                <this is a  test>"

echo "testing args:"
#run_output "$expected" ./center.py "                     <this is a  test> "

echo "testing stdin:"
run_output "$expected" ./center.py <<< "<this is a  test>"

expected="                                 <this is a test>"
echo "testing multi-args:"
run_output "$expected" ./center.py "<this" is a  "test> "


###########
# comment
expected="#                                 this is a test"

echo "testing args with # prefix:"
run_output "$expected" ./center.py " #  this is a test "

echo "testing stdin with # prefix:"
run_output "$expected" ./center.py <<< " # this is a test"

expected="//                                 this is a test"

echo "testing args with // prefix:"
run_output "$expected" ./center.py " //  this is a test "

echo "testing stdin with // prefix:"
run_output "$expected" ./center.py <<< " // this is a test"

###########
# comment handling disabled
expected="                               #  this is a test"

echo "testing args with # prefix with comment handling disabled:"
# doesn't preserve whitespace correctly
#run_output "$expected" ./center.py -n " #  this is a test "
result="$(./center.py -n " #  this is a test ")"
run++
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering args with # prefix with comment handling disabled"
else
    echo "Failed to center args with # prefix with comment handling disabled"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi
echo
hr

echo "testing stdin with # prefix with comment handling disabled:"
run_output "$expected" ./center.py -n <<< " #  this is a test"

expected="                               //  this is a test"

echo "testing args with // prefix with comment handling disabled:"
# doesn't preserve whitespace correctly
#run_output "$expected" ./center.py -n " //  this is a test "
result="$(./center.py -n " //  this is a test ")"
run++
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering args with // prefix with comment handling disabled"
else
    echo "Failed to center args with // prefix with comment handling disabled"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi
echo
hr

echo "testing stdin with // prefix:"
run_output "$expected" ./center.py -n <<< " //  this is a test"

#######################
# space in middle tests

expected="                         < t h i s   i s   a    t e s t >"

echo "testing spacing with arg:"
# doesn't preserve whitespace correctly
#run_output "$expected" ./center.py -s "                     <this is a  test> "
result="$(./center.py -s "                     <this is a  test> ")"
run++
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering args with // prefix with comment handling disabled"
else
    echo "Failed to center args with // prefix with comment handling disabled"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi
echo
hr

echo "testing spacing with stdin:"
run_output "$expected" ./center.py -s <<< "                     <this is a  test> "

echo
# $run_count defined in lib
# shellcheck disable=SC2154
echo "Completed $run_count tests"
echo
echo "All tests for center.py completed successfully"
echo
echo
