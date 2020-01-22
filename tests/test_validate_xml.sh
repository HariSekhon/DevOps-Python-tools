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

section "Testing validate_xml.py"

export TIMEOUT=3

if [ $# -gt 0 ]; then
    echo "validate_xml.py $*"
    ./validate_xml.py "$@"
    echo
fi

exclude='/tests/spark-\d+\.\d+.\d+-bin-hadoop\d+.\d+$|broken|error'

data_dir="tests/data"
broken_dir="tests/broken_xml"

rm -fr "$broken_dir" || :
mkdir "$broken_dir"

./validate_xml.py --exclude "$exclude" .
echo

echo "checking directory recursion (mixed with explicit file given)"
./validate_xml.py "$data_dir/plant_catalog.xml" .
echo

echo "checking symlink handling"
ln -sfv "simple.xml" "$data_dir/testlink.xml"
./validate_xml.py "$data_dir/testlink.xml"
rm "$data_dir/testlink.xml"
echo

echo "checking xml file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.xml' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_xml.py -t 1 "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_xml.py - < "$data_dir/simple.xml"
./validate_xml.py < "$data_dir/simple.xml"
# shellcheck disable=SC2094
./validate_xml.py "$data_dir/simple.xml" - < "$data_dir/simple.xml"
echo

echo "testing print mode"
[ "$(./validate_xml.py -p "$data_dir/simple.xml" | cksum)" = "$(cksum < "$data_dir/simple.xml")" ] || { echo "print test failed!"; exit 1; }
echo "successfully passed out test xml to stdout"
echo

echo "Now trying non-xml files to detect successful failure:"
check_broken(){
    local filename="$1"
    local expected_exitcode="${2:-2}"
    local options="${*:3}"
    set +e
    # shellcheck disable=SC2086
    ./validate_xml.py -t 1 $options "$filename"
    exitcode=$?
    set -e
    if [ "$exitcode" = "$expected_exitcode" ]; then
        echo "successfully detected broken xml in '$filename', returned exit code $exitcode"
        echo
    #elif [ $exitcode != 0 ]; then
    #    echo "returned unexpected non-zero exit code $exitcode for broken xml in '$filename'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $exitcode for broken xml in '$filename'"
        exit 1
    fi
}
# still works without the XML header
#sed -n '2,$p' "$data_dir/simple.xml" > "$broken_dir/simple.xml"
# break one from tag
sed -n 's/from/blah/; 2,$p' "$data_dir/simple.xml" > "$broken_dir/simple.xml"
check_broken "$broken_dir/simple.xml"

check_broken_sample_files xml

cat "$data_dir/simple.xml" >> "$broken_dir/multi-broken.xml"
cat "$data_dir/simple.xml" >> "$broken_dir/multi-broken.xml"

check_broken "$broken_dir/multi-broken.xml"

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
