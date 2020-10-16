#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2020-10-16 10:12:26 +0100 (Fri, 16 Oct 2020)
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
vpc_connector="cloud-sql-backups"  # for triggering across regions since Cloud Function may not be in the same region as the Cloud SQL instances to back up

gcloud functions deploy "$name" --trigger-topic "$topic" --runtime python37 --entry-point main --service-account "$service_account" --region "$region" --timeout 60 --vpc-connector "$vpc_connector" --memory 128MB
