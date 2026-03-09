import csv
import os
import sys

# --- VALIDACIÓN ---
if len(sys.argv) < 2:
    print("❌ Error: Falta el ID del proyecto.")
    sys.exit(1)

project = sys.argv[1] # <--- RECIBE EL PROYECTO
# ------------------

# Rutas dinámicas basadas en el argumento 'project'
base_path = "/mnt/datalake/openmind/MedP-Midas/sgonzalez/radiomics-midas-new/code/find"
archivo_hallazgos = f"{base_path}/resultados_espondilolistesis_{project}.csv"
archivo_metadatos = f"{base_path}/project_{project}.csv"
archivo_salida    = f"{base_path}/pacientes_con_espondilolistesis_{project}.csv"

print(f"--- Iniciando cruce (JOIN) para: {project} ---")

pacientes_con_patologia = set()

# PASO 1
if not os.path.exists(archivo_hallazgos):
    print(f"⚠️ No existe el archivo de hallazgos: {archivo_hallazgos}. Saltando JOIN.")
    sys.exit(1)

try:
    with open(archivo_hallazgos, mode='r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in reader.fieldnames]
        clave_hallazgo = 'Subject_ID' if 'Subject_ID' in headers else 'session_label'
        
        for row in reader:
            if clave_hallazgo in row:
                pacientes_con_patologia.add(row[clave_hallazgo].strip())
except Exception as e:
    print(f"Error leyendo hallazgos: {e}")
    sys.exit(1)

# PASO 2
if not os.path.exists(archivo_metadatos):
    print(f"⚠️ No existe el archivo de metadatos XNAT: {archivo_metadatos}. Saltando JOIN.")
    sys.exit(1)

try:
    with open(archivo_metadatos, mode='r', encoding='utf-8', errors='ignore') as f_in, \
         open(archivo_salida, mode='w', newline='', encoding='utf-8') as f_out:
        
        reader = csv.DictReader(f_in)
        columnas_salida = ['subject_id', 'session_label', 'patient_age','viwer_url']
        writer = csv.DictWriter(f_out, fieldnames=columnas_salida)
        writer.writeheader()
        
        filas_guardadas = 0
        for row in reader:
            label = row.get('session_label', '').strip()
            if label in pacientes_con_patologia:
                writer.writerow({
                    'subject_id': row.get('subject_id', ''),
                    'session_label': label,
                    'patient_age': row.get('patient_age', ''),
                    'viwer_url': row.get('viwer_url', '')
                })
                filas_guardadas += 1
                
    print(f"✅ JOIN completado. Filas generadas: {filas_guardadas}")

except Exception as e:
    print(f"Error en el cruce: {e}")