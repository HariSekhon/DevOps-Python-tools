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
#  http://www.linkedin.com/in/harisekhon
#

set -euo pipefail
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

./validate_xml.py -vvv $(
find "${1:-.}" -iname '*.xml' |
grep -v '/spark-.*-bin-hadoop.*/' |
grep -v -e 'broken' -e 'error' -e ' '
)
echo

echo "checking xml file without an extension"
cp -iv "$(find "${1:-.}" -iname '*.xml' | grep -v -e '/spark-.*-bin-hadoop.*/' -e 'broken' -e 'error' | head -n1)" no_extension_testfile
./validate_xml.py -vvv -t 1 no_extension_testfile
rm no_extension_testfile
echo

echo "testing stdin"
./validate_xml.py - < tests/simple.xml
./validate_xml.py < tests/simple.xml
./validate_xml.py tests/simple.xml - < tests/simple.xml
echo

echo "Now trying non-xml files to detect successful failure:"
check_broken(){
    f="$1"
    set +e
    ./validate_xml.py "$f"
    result=$?
    set -e
    if [ $result = 2 ]; then
        echo "successfully detected broken xml in '$f', returned exit code $result"
        echo
    #elif [ $result != 0 ]; then
    #    echo "returned unexpected non-zero exit code $result for broken xml in '$f'"
    #    exit 1
    else
        echo "FAILED, returned unexpected exit code $result for broken xml in '$f'"
        exit 1
    fi
}
check_broken tests/test.yaml
check_broken tests/test.json
check_broken README.md
cat tests/simple.xml >> tests/multi-broken.xml
cat tests/simple.xml >> tests/multi-broken.xml
check_broken tests/multi-broken.xml
rm tests/multi-broken.xml
echo "======="
echo "SUCCESS"
echo "======="

echo
echo
