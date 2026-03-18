from dotenv import load_dotenv
import requests

import os
import sys

# ESTO DEBE IR ANTES DE CUALQUIER OTRO IMPORT
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['transformers_verbosity'] = 'error'

import logging
import warnings

# Bloquear logs de raíz
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

# --- IMPORTS DE LOS AGENTES CON ALIAS ---
from Epidemiologia.agente import agent_respond as consultar_epidemiologia
from Cardiologia.agente import agent_respond as consultar_cardiologia
from Pediatria.agente import agent_respond as consultar_pediatria

current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLAMA_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# --- LÓGICA DEL MANAGER ---

def clasificar_y_decidir(pregunta):
    """
    El LLM actúa como triage médico para decidir qué especialistas consultar.
    """
    prompt_sistema = """Eres un coordinador médico de un hospital inteligente. 
    Tu trabajo es recibir una consulta y decidir qué especialistas deben intervenir:
    
    1. EPIDEMIOLOGIA: Para brotes, estadísticas de población, prevención y datos de salud pública.
    2. CARDIOLOGIA: Para enfermedades del corazón, hipertensión, arritmias y sistema circulatorio.
    3. PEDIATRIA: Para salud infantil, neonatología y enfermedades en niños o adolescentes.
    
    Responde ÚNICAMENTE con los nombres de los especialistas necesarios separados por comas (ejemplo: CARDIOLOGIA, PEDIATRIA)."""

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": pregunta}
        ],
        "temperature": 0 # Temperatura 0 para que sea preciso en la clasificación
    }
    
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=10)
        return res.json()["choices"][0]["message"]["content"].upper()
    except:
        return "EPIDEMIOLOGIA" # Fallback por seguridad

def sistema_agentico_multidisciplinario(pregunta_usuario):
    decision = clasificar_y_decidir(pregunta_usuario)
    print(f"\n[MANAGER]: Decisión de especialistas: {decision}\n")
    
    respuestas_expertos = []

    # Consultar Epidemiología
    if "EPIDEMIOLOGIA" in decision:
        print("-> Solicitando informe a Epidemiología...")
        res_epi = consultar_epidemiologia(pregunta_usuario) 
        respuestas_expertos.append(f"--- INFORME DE EPIDEMIOLOGÍA ---\n{res_epi}")

    # Consultar Cardiología
    if "CARDIOLOGIA" in decision:
        print("-> Solicitando informe a Cardiología...")
        res_cardio = consultar_cardiologia(pregunta_usuario)
        respuestas_expertos.append(f"--- INFORME DE CARDIOLOGÍA ---\n{res_cardio}")
    
    # Consultar Pediatría
    if "PEDIATRIA" in decision:
        print("-> Solicitando informe a Pediatría...")
        res_pediatria = consultar_pediatria(pregunta_usuario)
        respuestas_expertos.append(f"--- INFORME DE PEDIATRÍA ---\n{res_pediatria}")

    if not respuestas_expertos:
        return "No se encontró un especialista adecuado para esta consulta."

    # Unir todos los informes
    contexto_final = "\n\n".join(respuestas_expertos)
    return contexto_final

if __name__ == "__main__":
    print("=== SISTEMA MÉDICO MULTI-AGENTE ===\n")
    while True:
        pregunta = input("\nIngresa tu consulta médica: ").strip()
        
        if pregunta.lower() in ["salir", "exit"]:
            break
            
        if not pregunta:
            continue

        resultado = sistema_agentico_multidisciplinario(pregunta)
        
        print(resultado)
        print("="*30 + "\n")