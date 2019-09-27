#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-11-05 23:29:15 +0000 (Thu, 05 Nov 2015)
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

run_grep '/os.py[co]?$' ./find_python_library_path.py os
run_grep '/logging/__init__.py[co]?$' ./find_python_library_path.py logging
ERRCODE=2 run_grep '' ./find_python_library_path.py nonexistentmodule
run_grep 'python' ./find_python_library_path.py sys
ERRCODE=3 run_grep '' ./find_python_library_path.py
run_usage ./find_python_library_path.py
