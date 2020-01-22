#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-08-14 20:42:01 +0100 (Sun, 14 Aug 2016)
#
#  https://github.com/harisekhon/devops-python-tools
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

# shellcheck disable=SC1091
. "bash-tools/lib/utils.sh"

section "find_duplicate_files.py"

start_time="$(start_timer "find_duplicate_files.py test")"

testdir1="$(cd tests/data/ && mktemp -d -t tmp_find_duplicate_files.XXXXXX)"
testdir2="$(cd tests/data/ && mktemp -d -t tmp_find_duplicate_files2.XXXXXX)"

# shellcheck disable=SC2064,SC2086
trap "rm -fr '$testdir1' '$testdir2'" $TRAP_SIGNALS

echo test > "$testdir1/test1.txt"
echo nonmatching > "$testdir1/nonmatching.txt"

echo "checking no dups:"
run ./find_duplicate_files.py "$testdir1"

echo "checking no dups even when giving duplicate directory args:"
run ./find_duplicate_files.py "$testdir1" "$testdir1"

echo "checking no dups in quiet mode:"
run ./find_duplicate_files.py --quiet "$testdir1" "$testdir1"

for testdir in "$testdir1" "$testdir2"; do
    if [ "$testdir" = "$testdir1" ]; then
        msg2="in the same directory tree"
    else
        msg2="in different directory trees"
    fi

    echo "checking for dups by name $msg2:"
    mkdir "$testdir/2"
    echo different > "$testdir/2/test1.txt"
    echo
    run_fail 4 ./find_duplicate_files.py "$testdir" "$testdir1"

    rm "$testdir/2/test1.txt"

    echo "checking for dups by name in dot directories $msg2:"
    mkdir "$testdir/.3"
    echo different > "$testdir/.3/test1.txt"
    echo
    run_fail 4 ./find_duplicate_files.py --include-dot-dirs "$testdir" "$testdir1"
    echo
    echo "now check no dups found in hidden dot directory by default:"
    run ./find_duplicate_files.py "$testdir" "$testdir1"

    rm "$testdir/.3/test1.txt"

    echo "checking symlinks are not detected as duplicates by basename:"
    ln -s "$testdir/test1.txt" "$testdir2/test1.txt"
    run ./find_duplicate_files.py "$testdir" "$testdir2"
    rm -f "$testdir2/test1.txt"

    echo "checking .DS_Store files are ignored:"
    echo "DS_STORE" > "$testdir1/.DS_Store"
    cp "$testdir1/.DS_Store" "$testdir2/.DS_Store"
    run ./find_duplicate_files.py "$testdir" "$testdir2"

    rm -f "$testdir1/.DS_Store"  "$testdir2/.DS_Store"

    echo "checking for dups by size $msg2:"
    echo abcd > "$testdir/test2.txt"
    run_fail 4 ./find_duplicate_files.py --size "$testdir" "$testdir1"

    echo "checking dups by hash doesn't match on differing contents $msg2:"
    run ./find_duplicate_files.py --checksum "$testdir" "$testdir1"

    echo "and with no options specified $msg2:"
    run ./find_duplicate_files.py "$testdir" "$testdir1"

    rm "$testdir/test2.txt"

    echo "checking for dups by checksum $msg2:"
    echo test > "$testdir/test3.txt"
    run_fail 4 ./find_duplicate_files.py --checksum "$testdir" "$testdir1"

    rm "$testdir/test3.txt"

    echo "checking for dups by regex capture $msg2:"
    echo test2 > "$testdir/test2.txt"
    echo
    echo "first check no other method matches:"
    run ./find_duplicate_files.py "$testdir" "$testdir1"

    echo "now check the file basename matches on 'est'":
    run_fail 4 ./find_duplicate_files.py --regex 'est' "$testdir" "$testdir1" --quiet

    echo "now check the file basename matches with specified capture subset '(est)\d'":
    run_fail 4 ./find_duplicate_files.py --regex '(est)\d' "$testdir" "$testdir1"

    echo "now check the file basename doesn't match when the capture includes differing numbers 'est\d'":
    run ./find_duplicate_files.py --regex 'est\d' "$testdir" "$testdir1"

    rm "$testdir/test2.txt"

    echo "now check --quiet --no-short-circuit finds 3 duplicates":
    mkdir "$testdir/short-circuit"
    echo different > "$testdir/short-circuit/test1.txt"
    echo test      > "$testdir/short-circuit/test2.txt"
    run++
    set +o pipefail
    ./find_duplicate_files.py --quiet --no-short-circuit "$testdir" "$testdir1" | tee /dev/stderr | wc -l | grep "^[[:space:]]*3[[:space:]]*$" ||
        { echo "Failed to find expected 3 duplicates with --no-short-circuit! "; exit 1; }
    set -o pipefail
    echo
    rm "$testdir/short-circuit/test1.txt"
    rm "$testdir/short-circuit/test2.txt"
    hr
done

rm -fr "$testdir1" "$testdir2"

echo
echo
# $run_count defined in lib
# shellcheck disable=SC2154
echo "Tests run: $run_count"
time_taken "$start_time" "find_duplicate_files.py tests completed in"
echo
