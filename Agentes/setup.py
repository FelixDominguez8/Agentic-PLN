import fitz
import re
import os
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# ---------------- CONFIG ----------------
# pdf_files y collection_name ahora se reciben por parámetro en run_setup()
chunk_size = 500
embedding_model_name = "all-MiniLM-L6-v2"
current_dir = os.path.dirname(os.path.abspath(__file__))
chroma_db_dir = os.path.join(current_dir, "..", "chroma_db")
embedding_batch_size = 64
chroma_batch_size = 200
# ---------------------------------------

def extract_pages(pdf_paths):
    pages = []
    for path in pdf_paths:
        print(f"Procesando PDF: {path}")
        doc = fitz.open(path)
        pdf_name = os.path.basename(path)

        for i, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                pages.append({
                    "text": text,
                    "source": pdf_name,
                    "page": i + 1
                })
        doc.close()
    return pages

def chunk_text(pages):
    chunks = []
    for page in pages:
        text = re.sub(r'\s+', ' ', page["text"])
        words = text.split()

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append({
                "text": chunk,
                "source": page["source"],
                "page": page["page"]
            })
    return chunks

# Función para que setup_total.py le mande los datos de cada rama
def run_setup(collection_name, pdf_files):
    print("\nExtrayendo texto de PDFs...")
    pages = extract_pages(pdf_files)
    print(f"Total páginas procesadas: {len(pages)}")

    chunks = chunk_text(pages)
    print(f"Total chunks generados: {len(chunks)}")

    print("Cargando modelo de embeddings...")
    model = SentenceTransformer(embedding_model_name)

    texts = [c["text"] for c in chunks]
    print("Generando embeddings...")
    embeddings = model.encode(texts, batch_size=embedding_batch_size, show_progress_bar=True)

    print("Inicializando ChromaDB...")
    client = chromadb.PersistentClient(path=chroma_db_dir, settings=Settings())

    try:
        client.delete_collection(collection_name)
    except:
        pass

    collection = client.create_collection(name=collection_name)

    print("Insertando datos en ChromaDB...")
    ids, documents, metadatas, vectors = [], [], [], []

    for i, chunk in enumerate(chunks):
        ids.append(f"chunk_{i}")
        documents.append(chunk["text"])
        metadatas.append({"source": chunk["source"], "page": chunk["page"]})
        vectors.append(embeddings[i].tolist())

        if len(ids) >= chroma_batch_size:
            collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=vectors)
            ids, documents, metadatas, vectors = [], [], [], []
            print(f"{i+1}/{len(chunks)} chunks insertados")

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=vectors)

    print(f"\nBase de conocimiento creada en: {chroma_db_dir}")

if __name__ == "__main__":
    # Aquí puedes poner un ejemplo manual si quisieras probar este archivo solo
    pass