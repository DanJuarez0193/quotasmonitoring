variable "project_id" {
  description = "ID del proyecto donde se desplegará la infraestructura"
  type        = string
}

variable "region" {
  description = "Región de GCP"
  type        = string
  default     = "us-central1"
}

variable "org_id" {
  description = "ID numérico de la Organización (opcional)"
  type        = string
  default     = ""
}

variable "folder_ids" {
  description = "Lista de IDs de Folders a monitorear (opcional)"
  type        = list(string)
  default     = []
}

variable "bq_dataset_id" {
  description = "Nombre del dataset de BigQuery"
  type        = string
  default     = "quota_monitoring_ds"
}
