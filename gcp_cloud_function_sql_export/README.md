Google Cloud Function - SQL Backup Exporter to GCS
=====================

Triggers GCP [Cloud SQL](https://cloud.google.com/sql) export backups to [GCS](https://cloud.google.com/storage).

Solution documentation:

https://cloud.google.com/solutions/scheduling-cloud-sql-database-exports-using-cloud-scheduler

- `main.py` - the code
- `requirements.txt` - the pip modules to bootstrap
- `deploy.sh` - upload the code and deps

Upload the function to GCF in the current GCP project - this script will call `gcloud functions deploy` with the required switches:

```
./deploy.sh
```

### Solution Dependencies

- a [Cloud PubSub](https://cloud.google.com/pubsub) topic
- [Cloud Scheduler](https://cloud.google.com/scheduler) jobs to trigger backups
  - see `gcp_cloud_schedule_sql_exports.sh` in [DevOps Bash tools](https://github.com/HariSekhon/DevOps-Bash-tools/) repo
- a service account with permissions to access [Cloud SQL](https://cloud.google.com/sql)
  - see `gcp_sql_create_readonly_service_account.sh` in [DevOps Bash tools](https://github.com/HariSekhon/DevOps-Bash-tools/) repo
- each [Cloud SQL](https://cloud.google.com/sql) instance to be backed up requires objectCreator permissions to the [GCS](https://cloud.google.com/storage) bucket
  - see `gcp_sql_grant_instances_gcs_object_creator.sh` in [DevOps Bash tools](https://github.com/HariSekhon/DevOps-Bash-tools/) repo

### Serverless Framework

Instead of `deploy.sh` you can alternatively use the [Serverless](https://www.serverless.com/) framework for which a `serverless.yml` config is provided:

```
serverless deploy
```

If this is your first time using Serverless then you'll need to install the GCP plugin:

```
serverless plugin install --name serverless-google-cloudfunctions
```

The `serverless.yml` config expects to find `$GOOGLE_PROJECT_ID` and `$GOOGLE_REGION` environment variables.

Serverless requires additional permissions for the service account: Deployment Manager Editor and Storage Admin to create deployments and staging buckets.

You can also build a serverless artifact to `.serverless/` without deploying it (generates Google [Deployment Manager](https://cloud.google.com/deployment-manager) templates and a zip file - useful to check what would be uploaded / ignored):

```
serverless package
```
