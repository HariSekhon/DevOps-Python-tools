#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-03-05 18:27:00 +0000 (Tue, 05 Mar 2019)
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
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# shellcheck disable=SC1090
. "$srcdir/bash-tools/lib/utils.sh"

# re-establish srcdir local to this script since util.sh include brings its own srcdir
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# shellcheck disable=SC2120
usage(){
    if [ -n "$*" ]; then
        echo "$@" >&2
        echo >&2
    fi
    cat >&2 <<EOF

Splits a big file in to \$PARALLELISM parts (defaults to the number of CPU processors) and then runs that many parallel anonymize.py processes on the individual parts before concatenating back in to one big anonymized file

This makes it much, much faster to anonymize large log files for passing to vendors while maintaining the order of evaluation which is important for more specific matching before less specific matching

usage: ${0##*/} <files>

-p --parallelism    Number of parts to split files in to and anonymize in parallel before reconstituting
-h --help           Show usage and exit
EOF
    exit 3
}

parallelism="${PARALLELISM:-$(cpu_count)}"

file_list=""

while [ $# -gt 0 ]; do
    case $1 in
        -p|--parallel)  parallelism="$2"
                        shift
                        ;;
         -h|--help|-*)  usage
                        ;;
                    *)  file_list="$file_list $1"
                        ;;
    esac
    shift
done

for filename in $file_list; do
    echo
    echo "Processing file '$filename':"
    echo
    echo "Removing any pre-existing parts:"
    rm -v "$filename".* 2>/dev/null || :
    echo
    "$srcdir/bash-tools/split.sh" --parts "$parallelism" "$filename"
    echo "Anonymizing parts"
    for file_part in "$filename".*; do
        cmd="$srcdir/anonymize.py -a $file_part > $file_part.anonymized"
        echo "$cmd"
    done |
    parallel -j "$parallelism"
    echo "Concatenating parts"
    cat "$filename".*.anonymized > "$filename".anonymized
    echo
    echo "Removing parts:"
    rm -v "$filename".*.anonymized || :
    rm -v "$filename".[a-z0-9][a-z0-9] "$filename".[a-z0-9][a-z0-9][a-z0-9] 2>/dev/null || :
    echo
    echo "Anonymized file ready: $filename.anonymized"
    echo
done
