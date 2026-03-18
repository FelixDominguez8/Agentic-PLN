# agente.py mejorado (solo cambios solicitados)
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import requests
import os
from dotenv import load_dotenv
from langdetect import detect
import re

# ---------------- CONFIG ----------------
embedding_model_name = "all-MiniLM-L6-v2"
current_dir = os.path.dirname(os.path.abspath(__file__))
chroma_db_dir = os.path.join(current_dir, "..", "chroma_db")
collection_name = "cardiologia"
top_k = 5

# cargar variables del .env
load_dotenv(os.path.join(current_dir, "..", ".env"))

LLAMA_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ No se encontró GROQ_API_KEY en el archivo .env")
# ---------------------------------------

print("Cargando modelo de embeddings...")
model = SentenceTransformer(embedding_model_name)

print("Conectando con ChromaDB...")
client = chromadb.PersistentClient(path=chroma_db_dir, settings=Settings())
collection = client.get_collection(name=collection_name)


def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"


def remove_figure_sentences(text):
    """
    Elimina oraciones completas que dependan de figuras/tablas
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)

    cleaned = []
    for s in sentences:
        if re.search(r'\b(Figure|Figura|Table|Tabla)\b', s, re.IGNORECASE):
            continue  # eliminar oración completa
        cleaned.append(s)

    return " ".join(cleaned)


def retrieve_context(query):
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

        # 👉 ahora incluimos fuente dentro del contexto (IMPORTANTE)
        source = meta.get("source", "desconocido")
        page = meta.get("page", "?")

        context_parts.append(
            f"Fuente: {source} (página {page})\n{cleaned_doc}"
        )

    context = "\n\n".join(context_parts)
    return context


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
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=60
        )
        res.raise_for_status()
        data = res.json()
        
        # Validación de seguridad para evitar el "blanco"
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"].get("content", "")
            if not content:
                return "El modelo devolvió una respuesta vacía."
            return content
        return "Error: Estructura de respuesta inesperada."

    except Exception as e:
        return f"Error en la comunicación: {str(e)}"


def build_prompt(context, question):
    return f"""
    Eres un asistente especializado en Cardiología. Usa el CONTEXTO proporcionado para responder la PREGUNTA.

    Reglas Cruciales:
    - Responde basándote ÚNICAMENTE en el contexto.
    - Si el contexto menciona fármacos, dosis o procedimientos quirúrgicos, sé extremadamente preciso.
    - Si la información no está en el contexto, di honestamente que no cuentas con esos datos específicos en los manuales de cardiología cargados.
    - Ignora tablas o figuras que no tengan texto explicativo asociado.
    - Responde en el mismo idioma de la pregunta.

    Formato de salida:
    Respuesta: <tu respuesta clínica aquí>
    
    Fuentes: 
    - <Nombre del libro/PDF> (página X)

    CONTEXTO:
    {context}

    PREGUNTA:
    {question}
    """

def agent_respond(query):
    context = retrieve_context(query)
    lang = detect_language(query)

    system_prompt = (
        "Eres un cardiólogo experto y consultor médico. "
        "Tu objetivo es proporcionar análisis precisos sobre salud cardiovascular "
        "basándote exclusivamente en la evidencia del contexto proporcionado. "
        "Mantén un tono profesional, clínico y directo. "
        "Las respuetas basadas en el RAG no tienen que ser explicitas y no des notas que no son explicitas cuando claramente respondistes a la pregunta"
        f"El idioma de la respuesta debe ser {lang}."
    )

    max_tokens = 1800 if lang == "es" else 1500

    user_prompt = build_prompt(context, query)
    response = groq_chat(system_prompt, user_prompt, max_tokens=max_tokens)

    return response


# ---------------- CONSOLA ----------------
if __name__ == "__main__":
    print(f"\n🧠 Agente listo") # Cambia el nombre según la carpeta
    print("Escribe 'exit' para salir\n")

    # TODO ESTO DEBE ESTAR IDENTADO (DENTRO DEL IF)
    while True:
        try:
            q = input("Pregunta: ").strip()
            
            if not q:
                continue

            if q.lower() in ["exit", "salir"]:
                break

            respuesta = agent_respond(q)
            
            if respuesta and respuesta.strip():
                print("\n" + "="*20)
                print(respuesta.strip())
                print("="*20 + "\n")
            else:
                print("\n[!] El modelo no generó una respuesta.\n")

        except (EOFError, KeyboardInterrupt):
            break