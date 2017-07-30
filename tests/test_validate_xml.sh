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
#  https://www.linkedin.com/in/harisekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "
# ======================== #
# Testing validate_xml.py
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
broken_dir="tests/broken_xml"

rm -fr "$broken_dir" || :
mkdir "$broken_dir"
./validate_xml.py -vvv $(
find "${1:-.}" -iname '*.xml' |
grep -v '/spark-.*-bin-hadoop.*/' |
grep -v -e 'broken' -e 'error' -e ' '
)
echo

echo "checking directory recursion (mixed with explicit file given)"
./validate_xml.py -vvv "$data_dir/simple.xml" .
echo

echo "checking symlink handling"
ln -sfv "simple.xml" "$data_dir/testlink.xml"
./validate_xml.py "$data_dir/testlink.xml"
rm "$data_dir/testlink.xml"
echo

echo "checking xml file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.xml' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" "$broken_dir/no_extension_testfile"
./validate_xml.py -vvv -t 1 "$broken_dir/no_extension_testfile"
echo

echo "testing stdin"
./validate_xml.py - < "$data_dir/simple.xml"
./validate_xml.py < "$data_dir/simple.xml"
./validate_xml.py "$data_dir/simple.xml" - < "$data_dir/simple.xml"
echo

echo "testing print mode"
[ "$(./validate_xml.py -p "$data_dir/simple.xml" | cksum)" = "$(cksum < "$data_dir/simple.xml")" ] || { echo "print test failed!"; exit 1; }
echo "successfully passed out test xml to stdout"
echo

echo "Now trying non-xml files to detect successful failure:"
check_broken(){
    filename="$1"
    expected_exitcode="${2:-2}"
    set +e
    ./validate_xml.py -vvv "$filename" ${@:3}
    exitcode=$?
    set -e
    if [ $exitcode = $expected_exitcode ]; then
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
check_broken "$data_dir/test.yaml"
check_broken "$data_dir/test.json"
check_broken README.md
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
