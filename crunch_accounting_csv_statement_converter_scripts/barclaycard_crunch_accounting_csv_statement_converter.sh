#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-05-29 12:35:16 +0100 (Fri, 29 May 2020)
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
srcdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck disable=SC1090
#. "$srcdir/lib/utils.sh"

# statements should be named in format: Barclaycard_Statement_YYYY-MM-DD.csv
STATEMENT_GLOB="Barclaycard_Statement_[[:digit:]][[:digit:]][[:digit:]][[:digit:]]-[[:digit:]][[:digit:]]-[[:digit:]][[:digit:]].csv"

converter="$srcdir/../crunch_accounting_csv_statement_converter.py"

for statement in $STATEMENT_GLOB; do
    crunch_statement="${statement%.csv}_crunch.csv"
    if [ -f "$crunch_statement" ]; then
        latest_crunch_statement="$crunch_statement"
    fi
done

get_starting_balance(){
    local crunch_statement="$1"
    if ! [[ "$crunch_statement" =~ _crunch.csv$ ]]; then
        echo "invalid statement passed to get_starting_balance, must be *_crunch.csv" >&2
        exit 1
    fi
    tail -n 1 "$crunch_statement" | awk -F, '{print $4}'
}

if [ -n "${latest_crunch_statement:-}" ]; then
    echo "latest crunch statement is $latest_crunch_statement"
    starting_balance="$(get_starting_balance "$latest_crunch_statement")"
else
    starting_balance="${STARTING_BALANCE:-}"
    if [ -n "$starting_balance" ]; then
        echo "last crunch statement not found, you must specify the last balance manually via the environment variable \$LAST_BALANCE" >&2
        exit 1
    fi
fi

echo "starting balance: $starting_balance"

passed_latest_statement=0

for statement in $STATEMENT_GLOB; do
    crunch_statement="${statement%.csv}_crunch.csv"
    if [ -f "$crunch_statement" ]; then
        if [ "$crunch_statement" = "$latest_crunch_statement" ]; then
            passed_latest_statement=1
        fi
        continue
    fi
    if [ $passed_latest_statement -lt 1 ]; then
        continue
    fi
    "$converter" --credit-card --reverse-order --starting-balance "$starting_balance" "$statement"
    starting_balance="$(get_starting_balance "$crunch_statement")"
done
