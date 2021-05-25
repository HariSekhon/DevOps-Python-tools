Google Cloud Function - ifconfig
=====================

Queries http://ifconfig.co from GCF to check the routing and external IP being used eg. for comparison with Cloudflare / Firewall rules

- `main.py` - the code
- `requirements.txt` - the pip modules to bootstrap
- `deploy.sh` - upload the code and deps

Response is HTTP status code and message, then the raw JSON results

```
200 OK

{
  "ip": "1.2.3.4",
  "ip_decimal": 1234567890,
  "country": "United States",
  "country_iso": "US",
  "country_eu": false,
  "latitude": 37.751,
  "longitude": -97.822,
  "time_zone": "America/Chicago",
  "asn": "AS15169",
  "asn_org": "GOOGLE",
  "hostname": "ipv6.gae.googleusercontent.com",
  "user_agent": {
    "product": "python-requests",
    "version": "2.24.0",
    "raw_value": "python-requests/2.24.0"
  }
}
```

For IPv6 the format will be more like:
```
  "ip": "1234:5678:9012:34::a",
  "ip_decimal": 12345678901234567890123456789012345678,
```

Upload the function to GCF in the current GCP project - this script will call `gcloud functions deploy` with the required switches:

```
./deploy.sh
```
