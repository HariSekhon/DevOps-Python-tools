#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-09-27
#
#  https://github.com/harisekhon/devops-python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help improve or steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

set -eu
[ -n "${DEBUG:-}" ] && set -x
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$srcdir/..";

# shellcheck disable=SC1091
. ./tests/utils.sh

section "Python Find Library Path"

start_time="$(start_timer "python_find_library_path")"

run ./pythonpath.py

run_grep '/os.py[co]?$' ./python_find_library_path.py os
run_grep '/logging/__init__.py[co]?$' ./python_find_library_path.py logging
ERRCODE=2 run_grep '' ./python_find_library_path.py nonexistentmodule
run_grep 'python' ./python_find_library_path.py sys
run_grep 'python' ./python_find_library_path.py
run_usage ./python_find_library_path.py -
run_usage ./python_find_library_path.py --help

echo
# shellcheck disable=SC2154
echo "Total Tests run: $run_count"
time_taken "$start_time" "SUCCESS! All tests for python_find_library_path.py completed in"
echo
