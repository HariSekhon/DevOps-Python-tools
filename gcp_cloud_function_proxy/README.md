Google Cloud Function - Proxy
=====================

Queries a given URL from GCF to check connectivity eg. for testing with Cloudflare / Firewall rules

Query content:
```
{"url": "http://ifconfig.co/json"}
```

Response is HTTP status code and message, blank line and then the content:

```
200 OK

<raw_content>
```

- `main.py` - the code
- `requirements.txt` - the pip modules to bootstrap
- `deploy.sh` - upload the code and deps

Upload the function to GCF in the current GCP project - this script will call `gcloud functions deploy` with the required switches:

```
./deploy.sh
```
