#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-03-05 18:27:00 +0000 (Tue, 05 Mar 2019)
#
#  https://github.com/harisekhon/pytools
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

. "$srcdir/bash-tools/utils.sh"

# re-establish srcdir local to this script since util.sh include brings its own srcdir
srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

usage(){
    if [ -n "$*" ]; then
        echo "$@"
        echo
    fi
    cat <<EOF

Splits a big file in to \$PARTS parts (defaults to the number of CPU processors) and then runs that parallel anonymize.py processes on the parts before concatenating back in to one big anonymized file

This makes it much, much faster to anonymize large log files for passing to vendors

usage: ${0##*/} <files>

EOF
    exit 3
}

for x in $@; do
    case $x in
        -h|--help)  usage
                    ;;
    esac
done

parts="$(cpu_count)"

for filename in $@; do
    echo "Removing any pre-existing parts:"
    rm -v "$filename".* 2>/dev/null || :
    "$srcdir/bash-tools/split.sh" "$filename"
    echo "Anonymizing parts"
    for file_part in "$filename".*; do
        echo "$srcdir/anonymize.py -a $file_part > $file_part.anonymized"
    done |
    parallel -j "$parts"
    cat "$filename".*.anonymized > "$filename".anonymized
    echo "Removing parts:"
    rm -v "$filename".*.anonymized || :
    rm -v "$filename".[a-z0-9][a-z0-9] "$filename".[a-z0-9][a-z0-9][a-z0-9] 2>/dev/null || :
    echo "Anonymized file ready: $filename.anonymized"
done
echo "Done"
