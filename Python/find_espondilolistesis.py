import glob
import os
import csv
import sys  # <--- (1) Agregamos esta librería para recibir órdenes

# --- VALIDACIÓN DE ARGUMENTOS (NUEVO) ---
# Esto permite que el orquestador envíe el nombre del proyecto.
if len(sys.argv) < 2:
    print("❌ Error: Este script espera el ID del proyecto como argumento.")
    print("   Ejemplo de uso: python find_espondilolistesis.py p0012025")
    sys.exit(1)

# --- CONFIGURACIÓN ---
# (2) Aquí capturamos el proyecto que envía el script maestro
proyecto_id = sys.argv[1]  
# Antes tenías: proyecto_id = "p0012025"

ruta_base = f"/mnt/datalake/xnat2_data/archive/{proyecto_id}/arc001"
palabra_clave = "espondilolistesis"
nombre_csv = f"/mnt/datalake/openmind/MedP-Midas/sgonzalez/radiomics-midas-new/code/find/resultados_{palabra_clave}_{proyecto_id}.csv"
# ---------------------

print(f"🚀 INICIANDO BÚSQUEDA MASIVA EN: {ruta_base}")
print(f"🔎 Palabra clave: '{palabra_clave}'")
print(f"💾 Los resultados se guardarán en: {nombre_csv}\n")

# --- 1. PREPARACIÓN ---
# Extraemos el ID del proyecto automáticamente de la ruta (el padre de 'arc001')
project_id = os.path.basename(os.path.dirname(ruta_base))

# Abrimos el archivo CSV para escribir
archivo_csv = open(nombre_csv, mode='w', newline='', encoding='utf-8')
writer = csv.writer(archivo_csv)
# Escribimos los encabezados
writer.writerow(['Project_ID', 'session_label', 'Archivo', 'Contexto'])

# --- 2. LISTAR CARPETAS ---
patron_subjects = os.path.join(ruta_base, "*")
todas_carpetas = glob.glob(patron_subjects)
todas_carpetas.sort()

total_subjects = len(todas_carpetas)
print(f"📦 Total de carpetas (pacientes) a revisar: {total_subjects}")
print("-" * 60)

contador_hallazgos = 0

# --- 3. ITERAR SOBRE CADA PACIENTE ---
for i, carpeta_subject in enumerate(todas_carpetas, 1):
    subject_id = os.path.basename(carpeta_subject)
    
    # Construir ruta a los .txt
    ruta_txts = os.path.join(carpeta_subject, "RESOURCES", "sr", "*.txt")
    archivos = glob.glob(ruta_txts)
    
    # --- CASO 1: NO HAY ARCHIVOS ---
    if not archivos:
        print(f"[{i}/{total_subjects}] {subject_id}: ⚪ Sin archivos .txt (o sin carpeta sr)")
        continue

    # --- CASO 2: HAY ARCHIVOS, BUSCAMOS DENTRO ---
    encontrado_en_paciente = False
    detalles_hallazgo = [] # Para imprimir en consola
    filas_para_csv = []    # Para guardar en CSV

    for archivo in archivos:
        try:
            with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
                for num_linea, linea in enumerate(f, 1):
                    if palabra_clave.lower() in linea.lower():
                        encontrado_en_paciente = True
                        nombre_archivo = os.path.basename(archivo)
                        texto_limpio = linea.strip()
                        
                        # Guardamos info para mostrar luego en consola
                        detalles_hallazgo.append(f"   📄 {nombre_archivo} (Línea {num_linea}): {texto_limpio[:60]}...")
                        
                        # Guardamos info para el CSV (Proyecto, Paciente, Archivo, Texto)
                        filas_para_csv.append([project_id, subject_id, nombre_archivo, texto_limpio])
                        
        except Exception as e:
            print(f"   ⚠️ Error leyendo {os.path.basename(archivo)}: {e}")

    # --- IMPRIMIR RESULTADO Y GUARDAR EN CSV ---
    if encontrado_en_paciente:
        print(f"[{i}/{total_subjects}] {subject_id}: 🟢 ¡ENCONTRADO! 🟢")
        
        # 1. Imprimir en pantalla
        for detalle in detalles_hallazgo:
            print(detalle)
            
        # 2. Escribir en el CSV
        writer.writerows(filas_para_csv)
        
        contador_hallazgos += 1
    else:
        print(f"[{i}/{total_subjects}] {subject_id}: 🟡 Archivos revisados, palabra no encontrada.")

# Cerramos el archivo CSV al final
archivo_csv.close()

print("-" * 60)
print(f"🏁 FIN DEL PROCESO.")
print(f"Pacientes totales revisados: {total_subjects}")
print(f"Pacientes con mención de '{palabra_clave}': {contador_hallazgos}")
print(f"📂 Archivo CSV generado: {os.path.abspath(nombre_csv)}")