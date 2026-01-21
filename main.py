import io
import re
import pickle
import requests

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from docx import Document


# ======================================================
# APP  (i will expand it in college project)
# ======================================================
app = FastAPI(title="AI Resume Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================
# LOAD ML MODELS
# ======================================================
model = pickle.load(open("resume_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))


# ======================================================
# HELPERS
# ======================================================
def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text(file: UploadFile) -> str:
    content = file.file.read()

    if file.filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return " ".join(page.extract_text() or "" for page in reader.pages)

    if file.filename.lower().endswith(".docx"):
        doc = Document(io.BytesIO(content))
        return " ".join(p.text for p in doc.paragraphs)

    return ""


# ======================================================
# OLLAMA (QWEN 2.5 – NO FALLBACK)
# ======================================================
def call_ollama(resume_text: str, company: str, role: str) -> str:
    resume_text = resume_text[:1800]

    prompt = f"""
You are a senior ATS resume evaluator.

Analyze ONLY the resume.

Return STRICTLY in this format:

Strengths:
- ...

Weaknesses:
- ...

Improvement Areas:
- ...

Actionable Suggestions:
- ...

Target Company: {company}
Target Role: {role}

Resume:
{resume_text}
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:0.5b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 350
            }
        },
        timeout=60
    )

    response.raise_for_status()
    return response.json().get("response", "")


# ======================================================
# API ENDPOINT
# ======================================================
@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    resume_text = extract_text(resume)

    if not resume_text.strip():
        return {"error": "Unable to extract resume text"}

    # -------- ML SCORE --------
    cleaned = clean_text(resume_text)
    vec = vectorizer.transform([cleaned])

    predicted_category = model.predict(vec)[0]
    confidence = max(model.predict_proba(vec)[0]) * 100

    # -------- OLLAMA --------
    ai_output = call_ollama(resume_text, company, role)

    return {
        "company": company,
        "job_role": role,
        "predicted_category": predicted_category,
        "match_score": round(confidence, 2),
        "analysis": ai_output
    }
