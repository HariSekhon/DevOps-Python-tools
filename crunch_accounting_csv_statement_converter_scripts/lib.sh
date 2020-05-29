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

converter="$srcdir/../crunch_accounting_csv_statement_converter.py"

get_latest_crunch_statement(){
    local latest_crunch_statement
    for statement in $STATEMENT_GLOB; do
        crunch_statement="${statement%.csv}_crunch.csv"
        if [ -f "$crunch_statement" ]; then
            latest_crunch_statement="$crunch_statement"
        fi
    done
    if [ -n "${latest_crunch_statement:-}" ]; then
        echo "$latest_crunch_statement"
    fi
}

get_final_balance_from_statement(){
    local crunch_statement="$1"
    if ! [[ "$crunch_statement" =~ _crunch.csv$ ]]; then
        echo "invalid statement passed to get_final_balance_from_statement(), must be *_crunch.csv" >&2
        exit 1
    fi
    tail -n 1 "$crunch_statement" | awk -F, '{print $4}'
}

get_starting_balance(){
    local starting_balance
    local latest_crunch_statement="$1"
    if [ -n "${latest_crunch_statement:-}" ]; then
        echo "latest crunch statement is $latest_crunch_statement" >&2
        starting_balance="$(get_final_balance_from_statement "$latest_crunch_statement")"
    else
        echo "no latest crunch statement, getting starting balance from environment variable \$STARTING_BALANCE" >&2
        starting_balance="${STARTING_BALANCE:-}"
        if [ -z "$starting_balance" ]; then
            echo "last crunch statement not found, you must specify the last balance manually via the environment variable \$STARTING_BALANCE" >&2
            exit 1
        fi
    fi
    echo "starting balance: $starting_balance" >&2
    echo "$starting_balance"
}

generate_crunch_statements(){
    # only generate statements newer than the last generated one which provides the starting balance
    local passed_latest_statement=0
    local latest_crunch_statement
    local starting_balance
    latest_crunch_statement="$(get_latest_crunch_statement)"
    if [ -z "$latest_crunch_statement" ]; then
        passed_latest_statement=1
    fi
    starting_balance="$(get_starting_balance "$latest_crunch_statement")"
    for statement in $STATEMENT_GLOB; do
        crunch_statement="${statement%.csv}_crunch.csv"
        if [ -f "$crunch_statement" ]; then
            if [ $passed_latest_statement = 0 ] &&
               [ "$crunch_statement" = "$latest_crunch_statement" ]; then
                passed_latest_statement=1
            fi
            continue
        fi
        if [ $passed_latest_statement -lt 1 ]; then
            continue
        fi
        "$converter" "$@" --starting-balance "$starting_balance" "$statement"
        starting_balance="$(get_final_balance_from_statement "$crunch_statement")"
    done
}
