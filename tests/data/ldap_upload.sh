#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2019-04-11 18:57:53 +0100 (Thu, 11 Apr 2019)
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

# -a add
# -c continue on error (if already exists)

# Insufficient Permissions :-/
#ldapmodify -a -c -x -H ldap://localhost -D cn=admin,dc=example,dc=org -w admin -f "$srcdir/ldap_memberof_overlay.ldif"

# add
#ldapmodify -a -c -x -H ldap://localhost -D cn=admin,dc=example,dc=org -w admin -f "$srcdir/ldap.ldif" || :
ldapadd -c -x -H ldap://localhost -D cn=admin,dc=example,dc=org -w admin -f "$srcdir/ldap.ldif"

# modify
#ldapmodify -c -x -H ldap://localhost -D cn=admin,dc=example,dc=org -w admin -f "$srcdir/ldap.ldif"
