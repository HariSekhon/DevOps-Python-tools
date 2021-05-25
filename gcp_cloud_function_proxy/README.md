Google Cloud Function - Proxy
=====================

Queries a given URL from GCF to check connectivity eg. for testing with Cloudflare / Firewall rules

Query content:
```
{"url": "http://ifconfig.co/json"}
```

Response:

```
200 OK

<html_content>
```


- `main.py` - the code
- `requirements.txt` - the pip modules to bootstrap
- `deploy.sh` - upload the code and deps

Upload the function to GCF in the current GCP project - this script will call `gcloud functions deploy` with the required switches:

```
./deploy.sh
```
