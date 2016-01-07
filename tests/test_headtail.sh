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
# Testing headtail.py
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
broken_dir="$data_dir/broken_json_data"

if [ "$(./headtail.py tests/data/plant_catalog.xml | cksum)" = "1228592176 939" ]; then
    echo "headtail default success"
else
    echo "headtail default FAILED"
    exit 1
fi

if [ "$(./headtail.py tests/data/plant_catalog.xml -n 20 | cksum)" = "2465317856 1705" ]; then
    echo "headtail -n 20 success"
else
    echo "headtail -n 20 FAILED"
    exit 1
fi

echo
echo "======="
echo "SUCCESS"
echo "======="

echo
echo
