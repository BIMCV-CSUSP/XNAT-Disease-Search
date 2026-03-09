import subprocess
import logging
import time
import sys
from pyxnat import Interface 

# --- CONFIGURACIÓN ---
XNAT_USER = 'your_user'
XNAT_PASS = '***'  # <--- ⚠️ PON TU CONTRASEÑA AQUÍ
XNAT_URL = "https://xnat"

# 🛑 LISTA DE PROYECTOS A IGNORAR (Ya hechos manualmente)
PROYECTOS_YA_HECHOS = [
    "p0012025", 
    "p0032025",
    "p0042025",
    "p0182025"
]

# Nombres de tus scripts
SCRIPT_FIND = "find_espondilolistesis.py"
SCRIPT_EXTRACT = "extract_XNAT.py"
SCRIPT_JOIN = "join.py"

# Configurar Log
logging.basicConfig(
    filename='pipeline_global.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def obtener_proyectos_xnat():
    print("🔌 Conectando a XNAT para obtener lista de proyectos...")
    try:
        central = Interface(server=XNAT_URL, user=XNAT_USER, password=XNAT_PASS)
        # Obtenemos la lista de proyectos
        projects = central.select.projects().get()
        print(f"✅ Proyectos encontrados en XNAT: {len(projects)}")
        return projects
    except Exception as e:
        print(f"❌ Error conectando a XNAT: {e}")
        logging.error(f"Fallo conexión inicial XNAT: {e}")
        return []

def ejecutar_script(nombre_script, proyecto):
    """Ejecuta un script de python pasando el proyecto como argumento"""
    print(f"   > Ejecutando {nombre_script}...")
    try:
        result = subprocess.run(
            [sys.executable, nombre_script, proyecto],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Error en {nombre_script} para {proyecto}:\n{e.stderr}"
        print(f"   ❌ {error_msg}")
        logging.error(error_msg)
        return False

def main():
    projects_list = obtener_proyectos_xnat()
    
    if not projects_list:
        print("No hay proyectos para procesar.")
        return

    print(f"📋 Lista total: {len(projects_list)} proyectos.")
    print(f"🚫 Ignorando {len(PROYECTOS_YA_HECHOS)} proyectos manuales.")

    logging.info(f"Inicio de ciclo. Total disponibles: {len(projects_list)}")

    for idx, proj in enumerate(projects_list, 1):
        
        # --- FILTRO: SI EL PROYECTO ESTÁ EN LA LISTA NEGRA, SALTAR ---
        if proj in PROYECTOS_YA_HECHOS:
            print(f"\n[{idx}/{len(projects_list)}] ⏭️ Saltando {proj} (Marcado como YA HECHO).")
            continue
        # -------------------------------------------------------------

        print(f"\n[{idx}/{len(projects_list)}] 🚀 Procesando Proyecto: {proj}")
        logging.info(f"Iniciando {proj}")
        
        # 1. FIND (Busqueda en disco)
        if not ejecutar_script(SCRIPT_FIND, proj):
            print("   ⚠️ Falló la búsqueda. Saltando al siguiente proyecto.")
            continue 
            
        # 2. EXTRACT (Descarga de XNAT)
        if not ejecutar_script(SCRIPT_EXTRACT, proj):
            print("   ⚠️ Falló la extracción de XNAT. Saltando Join.")
            continue
            
        # 3. JOIN (Cruce final)
        ejecutar_script(SCRIPT_JOIN, proj)
        
        print(f"✅ Proyecto {proj} finalizado.")
        logging.info(f"Finalizado {proj}")
        
        # Pausa de seguridad
        time.sleep(2)

    print("\n🏁 Ejecución masiva completada.")

if __name__ == "__main__":
    main()