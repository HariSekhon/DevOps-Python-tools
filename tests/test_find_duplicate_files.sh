#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-08-14 20:42:01 +0100 (Sun, 14 Aug 2016)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

srcdir="$(cd "$(dirname "$0")" && pwd)"

cd "$srcdir/.."

. "bash-tools/utils.sh"

section "find_duplicate_files.py"

testdir="$(cd tests/data/ && mktemp -d -t tmp_find_duplicate_files)"
testdir2="$(cd tests/data/ && mktemp -d -t tmp_find_duplicate_files2)"

mkdir -v -p "$testdir"

echo test > "$testdir/test1.txt"
echo nonmatching > "$testdir/nonmatching.txt"

echo "checking no dups:"
echo
./find_duplicate_files.py "$testdir"
echo

hr

echo "checking for dups by name in same directory tree:"
mkdir "$testdir/2"
echo different > "$testdir/2/test1.txt"
echo
if ./find_duplicate_files.py "$testdir" "$testdir2"; then
    echo "Failed to find duplicate file in same directory tree"
    exit 1
fi
echo
rm "$testdir/2/test1.txt"

hr

echo "checking for dups by checksum in same directory tree:"
echo test > "$testdir/test2.txt"
echo
if ./find_duplicate_files.py "$testdir" "$testdir2"; then
    echo "Failed to find duplicate file in same directory tree"
    exit 1
fi
echo
rm "$testdir/test2.txt"

hr

echo "checking for dups by name across directory trees:"
echo different > "$testdir2/test1.txt"
echo
if ./find_duplicate_files.py "$testdir" "$testdir2"; then
    echo "Failed to find duplicate file by name in second directory tree"
    exit 1
fi
echo
rm "$testdir2/test1.txt"

hr

echo "checking for dups by checksum across directory trees:"
echo test > "$testdir2/test4.txt"
echo
if ./find_duplicate_files.py "$testdir" "$testdir2"; then
    echo "Failed to find duplicate file by checksum in second directory tree"
    exit 1
fi
echo

rm -fr "$testdir" "$testdir2"

echo
echo
