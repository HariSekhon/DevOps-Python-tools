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
. "$srcdir/lib.sh"

# statements should be named in format: Barclays_Statement_YYYY-MM-DD.csv
export STATEMENT_GLOB="Barclays_Statement_[[:digit:]][[:digit:]][[:digit:]][[:digit:]]-[[:digit:]][[:digit:]]-[[:digit:]][[:digit:]].csv"

# Barclays CSV statements often have whitespace starting fields instead of blank or 'null'
# unfortunately this resets all the original CSV timestamps each run so it's best to do only where needed
# UPDATE: no longer necessary, converter just ignores these blank fields now in the validation
#for statement in $STATEMENT_GLOB; do
    #perl -pi -e 's/^\s+,/,/' "$statement"
#done

generate_crunch_statements --reverse-order
