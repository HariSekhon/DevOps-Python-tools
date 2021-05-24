Google Cloud Function - SQL Backup Exporter to GCS
=====================

Queries a given URL from GCF to check connectivity eg. for testing with Cloudflare / Firewall rules

The query string should be like so:
```
{"url": "http://ifconfig.co/json"}
```

- `main.py` - the code
- `requirements.txt` - the pip modules to bootstrap
- `deploy.sh` - upload the code and deps

Upload the function to GCF in the current GCP project - this script will call `gcloud functions deploy` with the required switches:

```
./deploy.sh
```
