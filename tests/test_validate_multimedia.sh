#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-05-01 20:46:42 +0100 (Sun, 01 May 2016)
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
# Testing validate_multimedia.py
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
broken_dir="tests/media_broken"
test_file="$data_dir/sample.mp3"

if ! [ -f "$test_file" ]; then
    wget http://www.sample-videos.com/audio/mp3/crowd-cheering.mp3 -O "$test_file"
fi

rm -fr "$broken_dir" || :
mkdir "$broken_dir"
./validate_multimedia.py -vvv "$test_file" 
echo

echo "checking quick mode"
./validate_multimedia.py -vvv --quick "$test_file" 
echo

echo
echo "checking directory recursion (mixed with explicit file given)"
./validate_multimedia.py -vvv "$test_file" .
echo

echo "checking symlink handling"
ln -sfv "sample.mp3" "$data_dir/testlink.mp3"
./validate_multimedia.py "$data_dir/testlink.mp3"
rm "$data_dir/testlink.mp3"
echo

echo "checking media file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.mp3' | grep -v -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_multimedia.py -vvv "$broken_dir/no_extension_testfile"
echo

echo "Now trying non-media files to detect successful failure:"
check_broken(){
    filename="$1"
    expected_exitcode="${2:-2}"
    set +e
    ./validate_multimedia.py -vvv -t 1 "$filename" ${@:3}
    exitcode=$?
    set -e
    if [ $exitcode = $expected_exitcode ]; then
        echo "successfully detected broken media in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken media in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken media in '$filename'"
        exit 1
    fi
}
check_broken "$data_dir/multirecord.json"
# turns out this isn't broken and still plays
#echo 'blah' >  "$broken_dir/broken.mp3"
#cat "$test_file" >> "$broken_dir/broken.mp3"
#check_broken "$broken_dir/broken.mp3"
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
