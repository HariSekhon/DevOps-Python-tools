#!/usr/bin/env bash
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2021-05-24 16:34:19 +0100 (Mon, 24 May 2021)
#
#  https://github.com/HariSekhon/DevOps-Python-tools
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

name="ifconfig"

# Cloud Functions not available in all regions yet:
#
#   https://cloud.google.com/functions/docs/locations
#
# gcloud functions deploy doesn't seem to infer CLOUDSDK_COMPUTE_REGION from environment
region="$(gcloud config list --format="value(compute.region)" 2>&1 || :)"
region="${CLOUDSDK_COMPUTE_REGION:-${region:-europe-west1}}"

# https://console.cloud.google.com/marketplace/product/google/vpcaccess.googleapis.com
# for serverless VPC access to resources using their Private IPs
# since we're only accessing the SQL Admin API we don't need this
#vpc_connector="my-vpc-connector"

opts=()
if [ -n "${vpc_connector:-}" ]; then
    # routes all traffic through VPC connector to re-use the VPC's Cloud NAT IP eg. for permitting in firewall rules
    opts+=(--vpc-connector "$vpc_connector" --egress-settings all)
fi

set -x
gcloud functions deploy "$name" --trigger-http \
                                --security-level=secure-always \
                                --runtime python39 \
                                --entry-point main \
                                --memory 128MB \
                                --region "$region" \
                                --timeout 60 \
                                "${opts[@]}" \
                                --quiet  # don't prompt to --allow-unauthenticated
                                #--max-instances 1 \
