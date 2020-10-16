Google Cloud Function - SQL Backup Exporter to GCS
=====================

Triggers GCP [Cloud SQL](https://cloud.google.com/sql) export backups to [GCS](https://cloud.google.com/storage).

Solution documentation:

https://cloud.google.com/solutions/scheduling-cloud-sql-database-exports-using-cloud-scheduler

- `main.py` - the code
- `requirements.txt` - the pip modules to bootstrap
- `deploy.sh` - upload the code and deps

Upload the function to GCF in the current GCP project:

```
./deploy.sh
```

### Solution Dependencies

- [Cloud PubSub](https://cloud.google.com/pubsub) topic must exist
- [Cloud Scheduler](https://cloud.google.com/scheduler) jobs to trigger backups
  - see `gcp_cloud_schedule_sql_exports.sh` in [DevOps Bash tools](https://github.com/HariSekhon/DevOps-Bash-tools/) repo
- a service account with permissions to access [Cloud SQL](https://cloud.google.com/sql) and the [GCS](https://cloud.google.com/storage) bucket
  - see `gcp_sql_exports_create_service_account.sh` in [DevOps Bash tools](https://github.com/HariSekhon/DevOps-Bash-tools/) repo
