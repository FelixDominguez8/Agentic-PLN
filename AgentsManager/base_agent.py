# agente.py dinamizado
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import requests
import os
from dotenv import load_dotenv
from langdetect import detect
import re

# ---------------- CONFIG (Valores fijos) ----------------
embedding_model_name = "all-MiniLM-L6-v2"
current_dir = os.path.dirname(os.path.abspath(__file__))
chroma_db_dir = os.path.join(current_dir, "..", "chroma_db")
top_k = 5

# cargar variables del .env
load_dotenv(os.path.join(current_dir, "..", ".env"))

LLAMA_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ No se encontró GROQ_API_KEY en el archivo .env")
# ---------------------------------------------------------

print("Cargando modelo de embeddings...")
model = SentenceTransformer(embedding_model_name)

def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

def remove_figure_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    cleaned = []
    for s in sentences:
        if re.search(r'\b(Figure|Figura|Table|Tabla)\b', s, re.IGNORECASE):
            continue
        cleaned.append(s)
    return " ".join(cleaned)

def retrieve_context(query, collection):
    query_embedding = model.encode([query])[0].tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    context_parts = []

    for doc, meta in zip(documents, metadatas):
        cleaned_doc = remove_figure_sentences(doc)
        source = meta.get("source", "desconocido")
        page = meta.get("page", "?")
        context_parts.append(f"Fuente: {source} (página {page})\n{cleaned_doc}")

    return "\n\n".join(context_parts)

def groq_chat(system_prompt, user_prompt, max_tokens=1500):
    body = {
        "model": LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=60)
        res.raise_for_status()
        data = res.json()
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"].get("content", "")
            return content if content else "El modelo devolvió una respuesta vacía."
        return "Error: Estructura de respuesta inesperada."
    except Exception as e:
        return f"Error en la comunicación: {str(e)}"

# Prompt de Usuario Dinámico
def build_prompt(context, question, specialty):
    return f"""
    Eres un asistente médico especializado en {specialty}. 
    Tu tarea es responder la PREGUNTA usando exclusivamente el CONTEXTO.

    REGLAS CRÍTICAS DE RESPUESTA:
    1. Si la información no está en el contexto, di simplemente: "Información no disponible en los manuales actuales."
    2. PROHIBIDO usar frases como "No se proporciona más detalle", "En general la cardiología es...", o pedir más contexto.
    3. NO añadidas información de tus propios conocimientos externos.
    4. Termina tu respuesta INMEDIATAMENTE después de listar las fuentes.

    Formato de salida obligatorio:
    Respuesta: <tu respuesta técnica basada solo en el contexto>
    
    Fuentes utilizadas: 
    - <Nombre del archivo> (página X)

    CONTEXTO:
    {context}

    PREGUNTA:
    {question}
    """

# Función principal dinamizada
def agent_respond(query, collection_name):
    # Conexión dinámica a la colección solicitada
    client = chromadb.PersistentClient(path=chroma_db_dir, settings=Settings())
    collection = client.get_collection(name=collection_name)
    
    context = retrieve_context(query, collection)
    lang = detect_language(query)

    # System Prompt Dinámico
    system_prompt = (
        f"Eres un médico experto y especialista en {collection_name}. "
        f"Tu función es responder consultas médicas sobre {collection_name} de forma técnica y precisa. "
        "Es crucial que identifiques si la información del contexto especifica detalles clínicos clave. "
        "Tu tono debe ser profesional pero comprensible, basado estrictamente en el contexto. "
        f"El idioma de la respuesta debe ser {lang}."
    )

    max_tokens = 1800 if lang == "es" else 1500
    user_prompt = build_prompt(context, query, collection_name)
    
    response = groq_chat(system_prompt, user_prompt, max_tokens=max_tokens)

    if "Fuentes utilizadas:" in response:
        partes = response.split("Fuentes utilizadas:")
        respuesta_base = partes[0]
        
        lineas = partes[1].strip().split('\n')
        fuentes = [l for l in lineas if "(" in l and ")" in l]
        
        return f"{respuesta_base}Fuentes utilizadas:\n" + "\n".join(fuentes)

    
    return response.strip()

# ---------------- CONSOLA (Para pruebas manuales) ----------------
if __name__ == "__main__":
    test_branch = "pediatria" # Puedes cambiar esto para probar otras ramas
    print(f"\n🧠 Agente dinámico listo (Probando rama: {test_branch})")
    print("Escribe 'exit' para salir\n")

    while True:
        try:
            q = input("Pregunta: ").strip()
            if not q: continue
            if q.lower() in ["exit", "salir"]: break

            respuesta = agent_respond(q, test_branch)
            print("\n" + "="*20 + "\n" + respuesta.strip() + "\n" + "="*20 + "\n")
        except (EOFError, KeyboardInterrupt):
            break