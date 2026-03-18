import subprocess
import os

# Lista de carpetas y sus respectivos setups
setups = [
    ("Epidemiologia", "setup.py"),
    ("Cardiologia", "setup.py"),
    ("Pediatria", "setup.py")
]

print("--- INICIANDO PROCESAMIENTO DE TODOS LOS GRUPOS ---")

for carpeta, script in setups:
    # Construimos la ruta completa al archivo para verificar que existe
    ruta_script = os.path.join(carpeta, script)
    
    if os.path.exists(ruta_script):
        print(f"\n> Entrando a la carpeta '{carpeta}' y ejecutando {script}...")
        
        # El truco está en el parámetro 'cwd'
        # Esto hace que el script crea que está dentro de su propia carpeta
        resultado = subprocess.run(
            ["python", script], 
            cwd=carpeta,  # <--- ESTO ARREGLA EL ERROR DEL PDF
            capture_output=False
        )
        
        if resultado.returncode == 0:
            print(f"✅ {carpeta} terminado con éxito.")
        else:
            print(f"❌ Hubo un error en {carpeta}.")
    else:
        print(f"⚠️ No se encontró el archivo: {ruta_script}")

print("\n--- PROCESO FINALIZADO ---")