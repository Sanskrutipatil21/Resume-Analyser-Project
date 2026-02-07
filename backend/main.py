import io
import re
import os
import pickle
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from docx import Document
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# ======================================================
# APP
# ======================================================
app = FastAPI(title="AI Resume Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# FIREBASE INIT
# ======================================================
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")  # Your Firebase service account key
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ======================================================
# LOAD ML MODELS
# ======================================================
model = pickle.load(open("resume_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# ======================================================
# GROQ CLIENT
# ======================================================
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
# GROQ AI RESUME ANALYSIS
# ======================================================
def get_ai_analysis(resume_text: str, company: str, role: str) -> str:
    resume_text = resume_text[:1800]

    prompt = f"""
You are a senior ATS resume evaluator.

Analyze ONLY the resume below.

Return strictly in this format:

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

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are an expert resume analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_tokens=450
    )

    return response.choices[0].message.content.strip()

# ======================================================
# RESUME ANALYSIS ENDPOINT
# ======================================================
@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    user_id: str = Form(...),
):
    resume_text = extract_text(resume)
    if not resume_text.strip():
        return {"error": "Unable to extract resume text"}

    cleaned = clean_text(resume_text)
    vec = vectorizer.transform([cleaned])

    predicted_category = model.predict(vec)[0]
    confidence = max(model.predict_proba(vec)[0]) * 100  # This is the match score

    # AI Analysis
    analysis = get_ai_analysis(resume_text, company, role)

    # Save to Firestore
    doc_ref = db.collection("resumeHistory").document(user_id).collection("analyses").document()
    doc_ref.set({
        "analysis": analysis,
        "match_score": round(confidence, 2),  # <- fixed score
        "predicted_category": predicted_category,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {
        "doc_id": doc_ref.id,
        "match_score": round(confidence, 2),
        "analysis": analysis,
        "predicted_category": predicted_category
    }
