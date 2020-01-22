#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2016-05-01 20:46:42 +0100 (Sun, 01 May 2016)
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

section "Testing validate_multimedia.py"

export TIMEOUT=3

if ! type -P ffmpeg &>/dev/null; then
    # repos are broken on both Ubuntu until 15 and RHEL/CentOS :-(
    # not gonna cause major compilation for this when it works on my dev systems
    echo "WARNING: ffmpeg not installed, skipping validate_multimedia.py tests"
    exit 0
    if type -P apt-get &>/dev/null; then
        sudo apt-get install -y ffmpeg
    elif type -P yum &>/dev/null; then
        echo "WARNING: cannot auto-install ffmpeg on RHEL/CentOS, the 3rd party repos and deps are seriously broken"
    fi
fi

if [ $# -gt 0 ]; then
    echo "validate_multimedia.py $*"
    ./validate_multimedia.py "$@"
    echo
fi

data_dir="tests/data"
broken_dir="tests/media_broken"
test_file="$data_dir/sample.mp3"

if ! [ -f "$test_file" ]; then
    wget http://www.sample-videos.com/audio/mp3/crowd-cheering.mp3 -O "$test_file"
fi

rm -fr "$broken_dir" || :
mkdir "$broken_dir"
./validate_multimedia.py "$test_file"
echo

echo "checking quick mode"
./validate_multimedia.py --quick "$test_file"
echo

echo "checking directory recursion (mixed with explicit file given)"
./validate_multimedia.py "$test_file" .
echo

echo "checking regex with directory recursion"
./validate_multimedia.py "$test_file" -r '\.mp3$' .
echo

echo "checking symlink handling"
ln -sfv "sample.mp3" "$data_dir/testlink.mp3"
./validate_multimedia.py "$data_dir/testlink.mp3"
rm "$data_dir/testlink.mp3"
echo

echo "checking media file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.mp3' | grep -v -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_multimedia.py "$broken_dir/no_extension_testfile"
echo

check_broken(){
    local filename="$1"
    local expected_exitcode="${2:-2}"
    local options="${*:3}"
    set +e
    # shellcheck disable=SC2086
    ./validate_multimedia.py -t 1 $options "$filename"
    exitcode=$?
    set -e
    if [ "$exitcode" = "$expected_exitcode" ]; then
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
cp -av "$data_dir/test.csv" "$broken_dir/broken.mp3"
check_broken "$broken_dir/broken.mp3"
echo
echo "Checking failure with continue switch for entire tree"
check_broken . 2 "$test_file" -c
echo "Checking catches broken regex"
check_broken . 3 -r "*.mp3"
echo
echo "checking regex with directory recursion will skip broken file"
./validate_multimedia.py -r 'sample.mp3' .
echo

check_broken_sample_files mp3

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
