import os
import datetime
from google.cloud import monitoring_v3
from google.cloud import bigquery

def collect_quotas(event, context):
    project_id = os.environ.get('GCP_PROJECT')
    org_id = os.environ.get('MONITOR_ORG_ID')
    folder_ids = os.environ.get('MONITOR_FOLDERS', "").split(",")
    
    bq_client = bigquery.Client()
    monitoring_client = monitoring_v3.MetricServiceClient()
    table_id = f"{project_id}.quota_monitoring_ds.daily_quotas"

    now = datetime.datetime.now(datetime.timezone.utc)
    interval = monitoring_v3.TimeInterval({
        "end_time": {"seconds": int(now.timestamp())},
        "start_time": {"seconds": int((now - datetime.timedelta(hours=1)).timestamp())},
    })

    # Construir lista de scopes (Org y Folders)
    scopes = []
    if org_id:
        scopes.append(f"organizations/{org_id}")
    for f_id in folder_ids:
        if f_id.strip():
            scopes.append(f"folders/{f_id.strip()}")
    
    # Si no hay Org ni Folders, monitorear solo el proyecto local
    if not scopes:
        scopes.append(f"projects/{project_id}")

    rows_to_insert = []

    for scope in scopes:
        print(f"Consultando cuotas para scope: {scope}")
        try:
            results = monitoring_client.list_time_series(
                request={
                    "name": scope,
                    "filter": 'metric.type = starts_with("serviceruntime.googleapis.com/quota/allocation/")',
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.HEADERS,
                }
            )

            for series in results:
                quota_name = series.metric.labels.get("quota_metric", "unknown")
                target_project = series.resource.labels.get("project_id", "unknown")
                
                if series.points:
                    val = series.points[0].value.double_value
                    rows_to_insert.append({
                        "timestamp": now.isoformat(),
                        "project_id": target_project,
                        "quota_name": quota_name,
                        "usage": val if "usage" in series.metric.type else None,
                        "limit": val if "limit" in series.metric.type else None,
                    })
        except Exception as e:
            print(f"Error consultando {scope}: {e}")

    if rows_to_insert:
        errors = bq_client.insert_rows_json(table_id, rows_to_insert)
        if not errors:
            print(f"Éxito: {len(rows_to_insert)} registros insertados.")
        else:
            print(f"Errores en BQ: {errors}")
    
    return "Proceso completado"
