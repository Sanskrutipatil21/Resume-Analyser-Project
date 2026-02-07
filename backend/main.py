import io
import re
import os
import pickle
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from docx import Document
from groq import Groq
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Models
model = pickle.load(open("resume_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_text(file: UploadFile) -> str:
    content = file.file.read()
    if file.filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return " ".join(page.extract_text() or "" for page in reader.pages)
    return ""

@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    resume_text = extract_text(resume)
    cleaned_resume = clean_text(resume_text)
    
    # ML Scoring
    resume_vec = vectorizer.transform([cleaned_resume])
    target_text = clean_text(description if description.strip() else role)
    desc_vec = vectorizer.transform([target_text])
    
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    final_score = similarity * 100

    # --- FIX FOR 0% ---
    if final_score < 1:
        res_words = set(cleaned_resume.split())
        job_words = set(target_text.split())
        common = res_words.intersection(job_words)
        if job_words:
            final_score = (len(common) / len(job_words)) * 100

    # AI Analysis (Truncated prompt for brevity)
    analysis = "Strengths:\n- Example\nWeaknesses:\n- Example" # Get from Groq logic

    return {
        "company": company,
        "job_role": role, # This MUST match data.job_role in JS
        "score": round(final_score, 2),
        "analysis": analysis
    }
