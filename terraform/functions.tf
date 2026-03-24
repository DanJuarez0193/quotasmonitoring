# Bucket para el código fuente
resource "google_storage_bucket" "source_bucket" {
  name          = "${var.project_id}-quota-fn-source"
  location      = var.region
  force_destroy = true
}

# Empaquetar el código Python
data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "../function"
  output_path = "${path.module}/function.zip"
}

# Subir el Zip
resource "google_storage_bucket_object" "zip_object" {
  name   = "source.zip"
  bucket = google_storage_bucket.source_bucket.name
  source = data.archive_file.function_zip.output_path
}

# Crear la Cloud Function
resource "google_cloudfunctions_function" "quota_fn" {
  name        = "quota-collector-fn"
  runtime     = "python310"
  entry_point = "collect_quotas"

  source_archive_bucket = google_storage_bucket.source_bucket.name
  source_archive_object = google_storage_bucket_object.zip_object.name
  
  environment_variables = {
    MONITOR_ORG_ID  = var.org_id
    MONITOR_FOLDERS = join(",", var.folder_ids)
  }

  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.quota_topic.id
  }
}

# Cloud Scheduler (Diario 8:00 AM)
resource "google_cloud_scheduler_job" "quota_job" {
  name     = "quota-monitor-scheduler"
  schedule = "0 8 * * *"
  region   = var.region

  pubsub_target {
    topic_name = google_pubsub_topic.quota_topic.id
    data       = base64encode("start")
  }
}
