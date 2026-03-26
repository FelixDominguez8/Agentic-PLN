import os
import sys

# Añadimos la carpeta Agentes al path para poder importar el setup genérico
from setup_embeddings import run_setup

# ---------------- CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "AgentsData")
# ----------------------------------------

def regenerate_all_embeddings():
    print("\n--- INICIANDO REGENERACIÓN DINÁMICA DE EMBEDDINGS ---")

    # 1. Validar que la carpeta data exista
    if not os.path.exists(DATA_DIR):
        print(f"❌ Error: No se encontró la carpeta de datos en {DATA_DIR}")
        return

    # 2. Escanear automáticamente todas las subcarpetas en 'data/'
    # Cada subcarpeta (Cardiologia, Pediatria, etc.) será una colección
    ramas = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]

    if not ramas:
        print("⚠️ No se encontraron ramas médicas en la carpeta 'data/'.")
        return

    for rama in ramas:
        path_rama = os.path.join(DATA_DIR, rama)
        
        # 3. Listar todos los archivos PDF dentro de esa rama específica
        pdf_files = [
            os.path.join(path_rama, f) 
            for f in os.listdir(path_rama) 
            if f.lower().endswith('.pdf')
        ]

        if pdf_files:
            print(f"\n> Procesando rama: '{rama}' ({len(pdf_files)} PDFs encontrados)")
            try:
                # Llamamos a la función dinámica de tu Agentes/setup.py
                # Usamos el nombre de la carpeta como collection_name
                run_setup(collection_name=rama.lower(), pdf_files=pdf_files)
                print(f"✅ {rama} procesado con éxito.")
            except Exception as e:
                print(f"❌ Error procesando {rama}: {e}")
        else:
            print(f"⚠️ Saltando '{rama}': No contiene archivos PDF.")

    print("\n--- PROCESO FINALIZADO ---")

if __name__ == "__main__":
    regenerate_all_embeddings()