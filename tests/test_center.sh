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

. "bash-tools/utils.sh"

hr
echo "Testing center.py"
hr
echo

expected="                                <this is a  test>"

echo "testing args"
result="$(./center.py "                     <this is a  test> ")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering args"
else
    echo "Failed to center args"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

echo "testing stdin"
result="$(./center.py <<< "<this is a  test>")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering stdin"
else
    echo "Failed to center stdin"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

expected="                                 <this is a test>"
echo "testing multi-args"
result="$(./center.py "<this" is a  "test> ")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering multi-args"
else
    echo "Failed to center multi-args"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

###########
# comment
expected="#                                 this is a test"

echo "testing args with # prefix"
result="$(./center.py " #  this is a test ")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering args with # prefix"
else
    echo "Failed to center args with # prefix"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

echo "testing stdin with # prefix"
result="$(./center.py <<< " # this is a test")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering stdin with # prefix"
else
    echo "Failed to center stdin with # prefix"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

expected="//                                 this is a test"

echo "testing args with // prefix"
result="$(./center.py " //  this is a test ")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering args with // prefix"
else
    echo "Failed to center args with // prefix"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

echo "testing stdin with // prefix"
result="$(./center.py <<< " // this is a test")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering stdin with // prefix"
else
    echo "Failed to center stdin with // prefix"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

###########
# comment handling disabled
expected="                               #  this is a test"

echo "testing args with # prefix"
result="$(./center.py -n " #  this is a test ")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering args with # prefix"
else
    echo "Failed to center args with # prefix"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

echo "testing stdin with # prefix"
result="$(./center.py -n <<< " #  this is a test")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering stdin with # prefix"
else
    echo "Failed to center stdin with # prefix"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

expected="                               //  this is a test"

echo "testing args with // prefix"
result="$(./center.py -n " //  this is a test ")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering args with // prefix"
else
    echo "Failed to center args with // prefix"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

echo "testing stdin with // prefix"
result="$(./center.py -n <<< " //  this is a test")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering stdin with // prefix"
else
    echo "Failed to center stdin with // prefix"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi

echo "testing spacing"
expected="                         < t h i s   i s   a    t e s t >"
result="$(./center.py -s "                     <this is a  test> ")"
if [ "$result" = "$expected" ]; then
    echo "Succeeded in centering args with spacing between chars"
else
    echo "Failed to center args"
    echo "Expected: '$expected'"
    echo "Got:      '$result'"
    exit 1
fi
echo
hr
echo
