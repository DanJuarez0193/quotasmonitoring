import os
import requests
from datetime import datetime
import google.auth
from google.auth.transport.requests import Request
from google.cloud import bigquery
from google.cloud import resourcemanager_v3

def quota_collector(event, context):
    org_id = os.environ.get('ORG_ID', '929839340784')
    dataset_id = os.environ.get('DATASET_ID', 'quota_monitoring_ds')
    table_id = os.environ.get('TABLE_ID', 'daily_quotas')
    
    client_res = resourcemanager_v3.ProjectsClient()
    client_bq = bigquery.Client()
    
    credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    credentials.refresh(Request())
    headers = {'Authorization': f'Bearer {credentials.token}'}

    rows_to_insert = []
    timestamp = datetime.utcnow().isoformat()
    
    # Probemos con los dos servicios más garantizados de tener cuotas
    COMMON_SERVICES = ['compute.googleapis.com', 'iam.googleapis.com']

    try:
        query = f"parent:organizations/{org_id} state:ACTIVE"
        projects = client_res.search_projects(query=query)
        
        for project in projects:
            p_id = project.project_id
            print(f"--- Escaneando proyecto: {p_id} ---")
            
            for svc in COMMON_SERVICES:
                url = f"https://cloudquotas.googleapis.com/v1/projects/{p_id}/locations/global/services/{svc}/quotaInfos"
                resp = requests.get(url, headers=headers)
                
                if resp.status_code == 200:
                    data = resp.json()
                    quotas = data.get('quotaInfos', [])
                    print(f"Proyecto {p_id}: Encontradas {len(quotas)} cuotas para {svc}")
                    
                    for info in quotas:
                        u_val = float(info.get('quotaValue', 0))
                        
                        # Extraer límite con fallback a -1 para identificar si no existe el campo
                        l_val = -1.0
                        if info.get('containerThresholdConfigs'):
                            l_val = float(info['containerThresholdConfigs'][0].get('threshold', 0))

                        # FORZAMOS LA INSERCIÓN: Quitamos el filtro de limit > 0
                        rows_to_insert.append({
                            "timestamp": timestamp,
                            "project_id": p_id,
                            "quota_name": f"{svc}/{info.get('quotaId')}",
                            "usage": u_val,
                            "limit": l_val,
                            "percentage": (u_val / l_val * 100) if l_val > 0 else 0
                        })
                else:
                    print(f"Proyecto {p_id}: Servicio {svc} retornó error {resp.status_code}")

    except Exception as e:
        print(f"Error crítico: {str(e)}")
        return str(e)

    if rows_to_insert:
        print(f"Intentando insertar {len(rows_to_insert)} filas en BigQuery...")
        table_ref = client_bq.dataset(dataset_id).table(table_id)
        errors = client_bq.insert_rows_json(table_ref, rows_to_insert)
        if not errors:
            return f"EXITO: {len(rows_to_insert)} filas insertadas."
        else:
            print(f"ERRORES BQ: {errors}")
            return f"Error BQ: {errors}"
    
    return "No se generaron filas para insertar."