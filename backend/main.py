import io
import re
import os
import pickle
from pydantic import BaseModel  # Added for Study Plan JSON

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from docx import Document
from groq import Groq
from sklearn.metrics.pairwise import cosine_similarity

# ======================================================
# APP SETUP
# ======================================================
app = FastAPI(title="AI Career Assistant")

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
    prompt = f"Analyze this resume for {role} at {company}. Return Strengths, Weaknesses, Improvements, Suggestions."
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "Expert Resume Analyst"}, {"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

# ======================================================
# ENDPOINT 1: RESUME ANALYSIS (Existing - Untouched)
# ======================================================
@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    resume_text = extract_text(resume)
    if not resume_text.strip(): return {"error": "Empty resume"}

    cleaned_resume = clean_text(resume_text)
    resume_vec = vectorizer.transform([cleaned_resume])
    
    text_to_compare = description if description.strip() else role
    desc_vec = vectorizer.transform([clean_text(text_to_compare)])

    predicted_category = model.predict(resume_vec)[0]
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    match_score = similarity * 100

    analysis = get_ai_analysis(resume_text, company, role)

    return {
        "company": company, "job_role": role,
        "predicted_category": predicted_category,
        "match_score": round(match_score, 2), "analysis": analysis
    }

# ======================================================
# NEW: STUDY PLAN LOGIC (Added below)
# ======================================================

# Data structure to receive JSON from createplan.html
class StudyPlanRequest(BaseModel):
    resumeAnalysis: str
    targetRole: str
    targetCompany: str
    timeline: str
    dailyHours: str
    learningStyle: str = "Solo"
    planFormat: str = "Daily"
    challenges: str = ""

@app.post("/study-plan")
async def create_study_plan(data: StudyPlanRequest):
    prompt = f"""
    Create a {data.planFormat} study plan for {data.targetRole} at {data.targetCompany}.
    Timeline: {data.timeline} ({data.dailyHours}/day).
    Style: {data.learningStyle}. 
    Challenge: {data.challenges}.
    
    Context from Resume: {data.resumeAnalysis}
    
    Format in Markdown with Phase-by-Phase breakdown and specific resources.
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "Professional Career Coach"}, {"role": "user", "content": prompt}],
        temperature=0.5,
    )
    
    return {"study_plan": response.choices[0].message.content}
