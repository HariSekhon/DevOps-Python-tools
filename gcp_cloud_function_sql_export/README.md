Google Cloud Function - SQL Backup Exporter to GCS
=====================

Triggers GCP [Cloud SQL](https://cloud.google.com/sql) export backups to [GCS](https://cloud.google.com/storage).

Solution documentation:

https://cloud.google.com/solutions/scheduling-cloud-sql-database-exports-using-cloud-scheduler

`main.py` - the code
`requirements.txt` - the pip modules to bootstrap
`deploy.sh` - upload the code and deps

Upload the function to GCF in the current GCP project:

```
./deploy.sh
```

### Solution Dependencies

- [Cloud PubSub](https://cloud.google.com/pubsub) topic must exist
- [Cloud Scheduler](https://cloud.google.com/scheduler) must be set to trigger notifications on schedule for any instances and databases in those instances you want backed up to GCS
- service account with permissions to access [Cloud SQL](https://cloud.google.com/sql) and the [GCS](https://cloud.google.com/storage) bucket

See [DevOps Bash tools] repo which has scripts to idempotently create the service account and permissions, and also set up the [Cloud Scheduler](https://cloud.google.com/scheduler) jobs for every running non-replica instance and database in the current project.
