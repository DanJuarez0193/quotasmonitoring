provider "google" {
  project = var.project_id
  region  = var.region
}

# Dataset de BigQuery
resource "google_bigquery_dataset" "quota_ds" {
  dataset_id = var.bq_dataset_id
  location   = var.region
}

# Tabla de BigQuery
resource "google_bigquery_table" "quota_table" {
  dataset_id          = google_bigquery_dataset.quota_ds.dataset_id
  table_id            = "daily_quotas"
  deletion_protection = false

  schema = <<EOF
[
  {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "project_id", "type": "STRING", "mode": "REQUIRED"},
  {"name": "quota_name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "limit", "type": "FLOAT", "mode": "NULLABLE"},
  {"name": "usage", "type": "FLOAT", "mode": "NULLABLE"}
]
EOF
}

# Tópico de Pub/Sub
resource "google_pubsub_topic" "quota_topic" {
  name = "run-quota-collection"
}
