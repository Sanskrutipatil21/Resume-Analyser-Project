import io
import re
import os
import pickle
from pydantic import BaseModel
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

# Load local ML models
model = pickle.load(open("resume_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- DATA MODELS ---
class StudyPlanRequest(BaseModel):
    resumeAnalysis: str
    targetRole: str
    targetCompany: str
    timeline: str
    dailyHours: str
    learningStyle: str
    planFormat: str
    challenges: str

# --- HELPERS ---
def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_text(file: UploadFile) -> str:
    content = file.file.read()
    if file.filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return " ".join(page.extract_text() or "" for page in reader.pages)
    elif file.filename.lower().endswith(".docx"):
        doc = Document(io.BytesIO(content))
        return " ".join(p.text for p in doc.paragraphs)
    return ""

def get_ai_analysis(resume_text, company, role):
    prompt = f"Analyze resume for {role} at {company}. Provide Strengths, Weaknesses, and Improvement Areas. Resume: {resume_text[:2000]}"
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content

# --- ENDPOINT 1: RESUME ANALYZER ---
@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    resume_text = extract_text(resume)
    if not resume_text.strip(): return {"error": "Empty Resume"}

    cleaned_resume = clean_text(resume_text)
    resume_vec = vectorizer.transform([cleaned_resume])
    
    # Scoring Logic
    target_text = clean_text(description if description.strip() else role)
    desc_vec = vectorizer.transform([target_text])
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    
    # Fallback score if description is empty
    match_score = similarity * 100 if description.strip() else max(model.predict_proba(resume_vec)[0]) * 100
    if match_score < 10 and role.lower() in cleaned_resume: match_score = 35.0

    analysis = get_ai_analysis(resume_text, company, role)

    return {
        "predicted_category": model.predict(resume_vec)[0],
        "match_score": round(match_score, 2),
        "analysis": analysis
    }

# --- ENDPOINT 2: STUDY PLAN GENERATOR ---
@app.post("/study-plan")
async def create_study_plan(data: StudyPlanRequest):
    prompt = f"""
    Generate a {data.planFormat} roadmap for {data.targetRole} at {data.targetCompany}.
    Timeline: {data.timeline}, Hours/Day: {data.dailyHours}, Style: {data.learningStyle}.
    Challenges: {data.challenges}.
    Base it on this resume feedback: {data.resumeAnalysis}
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"study_plan": response.choices[0].message.content}
