# api/app/main.py
import os
import time
import requests
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from dotenv import load_dotenv
load_dotenv()



# Intentamos transformers; si falla, seguiremos sin generación (solo RAG).
try:
    from transformers import pipeline, set_seed
    GEN_AVAILABLE = True
except Exception:
    GEN_AVAILABLE = False

DATA_DIR = Path("/data")
PDF_DIR = DATA_DIR / "pdfs"
OUT_DIR = DATA_DIR / "output"

PDF_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

DI_ENDPOINT = os.getenv("DOC_INTELLIGENCE_ENDPOINT", "")
DI_KEY = os.getenv("DOC_INTELLIGENCE_KEY", "")

app = FastAPI(title="RAG+DocInt Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vector index state
_docs: Dict[str, str] = {}        # filename -> text
_vectorizer: TfidfVectorizer = None
_matrix = None

# Load generation pipeline
_gen = None
if GEN_AVAILABLE:
    try:
        # usa distilgpt2 para ser más ligero
        _gen = pipeline("text-generation", model="distilgpt2")
        set_seed(42)
    except Exception:
        _gen = None
        GEN_AVAILABLE = False

def call_doc_intelligence(pdf_path: str) -> str:
    """Llama al endpoint de Document Intelligence (REST) para extraer texto del PDF."""
    if not DI_ENDPOINT or not DI_KEY:
        raise RuntimeError("Faltan DI_ENDPOINT o DI_KEY en las variables de entorno.")
    url = f"{DI_ENDPOINT.rstrip('/')}/documentModels/prebuilt-read:analyze?api-version=2024-02-29-preview"
    with open(pdf_path, "rb") as f:
        data = f.read()
    headers = {
        "Ocp-Apim-Subscription-Key": DI_KEY,
        "Content-Type": "application/pdf"
    }
    resp = requests.post(url, headers=headers, data=data, timeout=120)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"DI failed: {resp.status_code} {resp.text}")
    j = resp.json()
    content = ""
    if isinstance(j, dict):
        content = j.get("content", "")
        if not content and "documents" in j:
            try:
                content = j["documents"][0].get("content", "")
            except Exception:
                content = ""
        if not content and "pages" in j:
            lines = []
            for p in j["pages"]:
                for l in p.get("lines", []):
                    lines.append(l.get("content", ""))
            content = "\n".join(lines)
    return content

def index_all_texts():
    global _docs, _vectorizer, _matrix
    _docs = {}
    for txt in OUT_DIR.glob("*.txt"):
        try:
            text = txt.read_text(encoding="utf-8")
        except:
            text = txt.read_text(encoding="latin-1")
        _docs[txt.name] = text
    if not _docs:
        _vectorizer = None
        _matrix = None
        return
    _vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=20000)
    corpus = list(_docs.values())
    _matrix = _vectorizer.fit_transform(corpus)
    return

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "API running"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse({"error":"solo PDFs"}, status_code=400)
    dest = PDF_DIR / file.filename
    with open(dest, "wb") as f:
        content = await file.read()
        f.write(content)
    try:
        extracted = call_doc_intelligence(str(dest))
    except Exception as e:
        return JSONResponse({"error": "DI failed", "detail": str(e)}, status_code=500)
    out_file = OUT_DIR / (file.filename + ".txt")
    out_file.write_text(extracted or "", encoding="utf-8")
    index_all_texts()
    return {"status":"ok","filename":file.filename}

@app.post("/reindex")
def reindex():
    index_all_texts()
    return {"status":"ok","num_docs": len(_docs)}

def retrieve(query: str, top_k: int = 3):
    if not _vectorizer or _matrix is None or not _docs:
        return []
    qv = _vectorizer.transform([query])
    scores = (_matrix @ qv.T).toarray().squeeze()
    idx = np.argsort(scores)[::-1][:top_k]
    keys = list(_docs.keys())
    results = []
    for i in idx:
        if scores[i] <= 0:
            continue
        results.append({"filename": keys[i], "score": float(scores[i]), "text": _docs[keys[i]]})
    return results

@app.get("/query")
def query(q: str = "", top_k: int = 3):
    if not q:
        return {"error":"query empty"}, 400
    retrieved = retrieve(q, top_k=top_k)
    context_parts = []
    filenames = []
    for r in retrieved:
        filenames.append(r["filename"])
        snippet = r["text"][:1500]
        context_parts.append(f"--- FILE: {r['filename']} ---\n{snippet}\n")
    context = "\n\n".join(context_parts)
    prompt = (
        "You are a helpful assistant. Use ONLY the information in the documents below to answer the question. "
        "If the info is not present, say so.\n\n"
        f"{context}\n\nQUESTION: {q}\n\nAnswer in clear English. Also include which files support your answer (filenames)."
    )

    if GEN_AVAILABLE and _gen is not None:
        try:
            got = _gen(prompt, max_length=256, num_return_sequences=1, do_sample=False)
            answer = got[0]["generated_text"]
            if prompt in answer:
                answer = answer.split(prompt,1)[-1].strip()
        except Exception as e:
            answer = f"[generation failed: {e}]"
    else:
        answer = "Retrieved documents:\n" + "\n".join([f"{r['filename']} (score={r['score']:.3f})" for r in retrieved])

    return {"query": q, "answer": answer, "files": filenames, "retrieved": retrieved}
