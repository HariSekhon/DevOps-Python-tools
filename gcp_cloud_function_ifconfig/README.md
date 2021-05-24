Google Cloud Function - SQL Backup Exporter to GCS
=====================

Queries http://ifconfig.co from GCF to check the routing and external IP being used eg. for comparison with Cloudflare / Firewall rules

- `main.py` - the code
- `requirements.txt` - the pip modules to bootstrap
- `deploy.sh` - upload the code and deps

Upload the function to GCF in the current GCP project - this script will call `gcloud functions deploy` with the required switches:

```
./deploy.sh
```
