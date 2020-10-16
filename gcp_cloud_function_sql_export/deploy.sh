#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-10-16 10:12:26 +0100 (Fri, 16 Oct 2020)
#
#  https://github.com/HariSekhon/pytools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/HariSekhon
#

set -euo pipefail
[ -n "${DEBUG:-}" ] && set -x
srcdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$srcdir"

project="$(gcloud config list --format="value(core.project)")"
region="europe-west3"  # not available in all regions yet

name="cloud-sql-backups"
topic="cloud-sql-backups"
service_account="cloud-function-sql-backup@$project.iam.gserviceaccount.com"
# https://console.cloud.google.com/marketplace/product/google/vpcaccess.googleapis.com
# for serverless VPC access to resources using their Private IPs
# since we're only accessing the SQL Admin API we don't need this
#vpc_connector="cloud-sql-backups"

gcloud functions deploy "$name" --trigger-topic "$topic" --runtime python37 --entry-point main --service-account "$service_account" --region "$region" --timeout 60 --memory 128MB # --vpc-connector "$vpc_connector"
