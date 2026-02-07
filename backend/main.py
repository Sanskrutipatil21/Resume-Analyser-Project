import io
import re
import os
import pickle

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from docx import Document
from groq import Groq
from sklearn.metrics.pairwise import cosine_similarity

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

    # 1. Vectorize
    cleaned_resume = clean_text(resume_text)
    resume_vec = vectorizer.transform([cleaned_resume])

    # 2. Match Score
    text_to_compare = description if description.strip() else role
    desc_vec = vectorizer.transform([clean_text(text_to_compare)])
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    
    # Calculate Score
    final_score = round(similarity * 100, 2)
    
    # AI Analysis
    analysis_text = get_ai_analysis(resume_text, company, role)

    # RETURN KEYS MATCHING RESULT.HTML
    return {
        "company": company,
        "job_role": role,
        "score": final_score,
        "analysis": analysis_text
    }
