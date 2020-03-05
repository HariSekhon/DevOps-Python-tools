#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2015-05-25 01:38:24 +0100 (Mon, 25 May 2015)
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

# shellcheck disable=SC2068
for x in ${@:-$(echo ./*.py 2>/dev/null)}; do
    isExcluded "$x" && continue
    set +e
    echo "$x --help"
    "$x" --help # >/dev/null
    status=$?
    set -e
    echo; hr
    if [ $status = 0 ]; then
        [[ "$x" =~ ambari_blueprints.py$ ]] && continue
        [[ "$x" =~ pythonpath.py$ ]] && continue
        [[ "$x" =~ aws_s3_presign.py$ ]] && continue
    elif [ $status = 1 ]; then
        if [[ "$x" =~ hdfs_find_replication_factor_1.py$ ]] &&
           ! python -c 'import krbV'; then  # best effort, not available on Mac any more
            continue
        fi
    fi
    [ $status = 3 ] || { echo "status code for $x --help was $status not expected 3"; exit 1; }
done
echo "All Python programs found exited with expected code 0/3 for --help"
