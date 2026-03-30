from dotenv import load_dotenv
import requests
import os
import sys

# Bloqueo de logs innecesarios
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import logging
import warnings
logging.getLogger("transformers").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

# Import único del agente dinámico
from AgentsManager.base_agent import agent_respond

# --- CONFIGURACIÓN ---
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "AgentsData")
load_dotenv(os.path.join(current_dir, ".env"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLAMA_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Obtener lista de especialidades disponibles desde la carpeta data
def obtener_especialidades():
    if not os.path.exists(DATA_DIR):
        return []
    return [d.upper() for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]

def clasificar_y_decidir(pregunta, especialidades):
    lista_especialidades = "\n".join([f"- {e}" for e in especialidades])
    
    prompt_sistema = f"""Eres un clasificador de consultas médicas.
    Tu ÚNICA función es identificar qué especialistas de esta lista son necesarios: [{lista_especialidades}].
    
    Reglas estrictas:
    1. Responde ÚNICAMENTE con los nombres de los especialistas separados por comas.
    2. NO respondas la pregunta del usuario.
    3. NO des definiciones ni explicaciones.
    4. Si no sabes, responde: {especialidades[0]}"""

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": pregunta}
        ],
        "temperature": 0
    }
    
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=10)
        return res.json()["choices"][0]["message"]["content"].upper()
    except:
        return especialidades[0] if especialidades else ""

def sistema_agentico_multidisciplinario(pregunta_usuario):
    especialidades_disponibles = obtener_especialidades()
    decision = clasificar_y_decidir(pregunta_usuario, especialidades_disponibles)
    print(f"\n[MANAGER]: Decisión de especialistas: {decision}\n")
    
    respuestas_expertos = []

    # Iteramos sobre la decisión del LLM
    for rama in especialidades_disponibles:
        if rama in decision:
            print(f"-> Solicitando informe a {rama}...")
            # Llamamos al agente pasando el nombre de la colección (en minúsculas para ChromaDB)
            res_agente = agent_respond(pregunta_usuario, rama.lower())
            respuestas_expertos.append(f"--- INFORME DE {rama} ---\n{res_agente}")

    if not respuestas_expertos:
        return "No se encontró un especialista adecuado para esta consulta."

    return "\n\n".join(respuestas_expertos)

if __name__ == "__main__":
    print("=== SISTEMA MÉDICO MULTI-AGENTE DINÁMICO ===\n")
    while True:
        pregunta = input("\nIngresa tu consulta médica: ").strip()
        if pregunta.lower() in ["salir", "exit"]: break
        if not pregunta: continue

        resultado = sistema_agentico_multidisciplinario(pregunta)
        print(resultado)
        print("="*30 + "\n")