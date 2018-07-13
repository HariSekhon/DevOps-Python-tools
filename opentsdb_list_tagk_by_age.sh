#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2018-07-13 22:36:14 +0100 (Fri, 13 Jul 2018)
#
#  https://github.com/harisekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/harisekhon
#

# Quick script to list OpenTSDB tag keys by age via local HBase Shell

# Output:
#
# <timestamp_epoch_millis>  <human_timestamp>   <tagk>

# Tested on OpenTSDB 2.3 on HBase 1.4

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x

for path in {,/opt}/hbase/bin; do
    if [ -d "$path" ]; then
        export PATH="$PATH:$path"
    fi
done

if ! which hbase &>/dev/null; then
    echo "hbase command not found in \$PATH ($PATH)"
    exit 1
fi

# hackish but convenient - forking to date thousands or hundreds of thousands of times can take hours, python takes 10 secs even for 250,000+ metrics
tmp_python_script=$(mktemp)
cat > "$tmp_python_script" <<EOF
import sys, time
for line in sys.stdin:
    (ts, metric) = line.split()
    print "{}\t{}\t{}".format(ts, time.strftime("%F %T", time.localtime(int(ts)/1000)), metric)
EOF
trap "rm '$tmp'" EXIT

hbase shell <<< "scan 'tsdb-uid', { COLUMNS => 'name:tagk', VERSIONS => 1 }" 2>/dev/null |
grep 'value=' |
sed 's/^.*, timestamp=//; s/, value=/ /' |
python "$tmp_python_script" |
sort -k1n
