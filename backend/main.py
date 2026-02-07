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

# ======================================================
# APP & MODELS
# ======================================================
app = FastAPI(title="AI Career Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = pickle.load(open("resume_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ======================================================
# DATA MODELS
# ======================================================
class StudyPlanRequest(BaseModel):
    resumeAnalysis: str
    targetRole: str
    targetCompany: str
    timeline: str
    dailyHours: str
    learningStyle: str = "Solo"
    planFormat: str = "Daily"
    challenges: str = ""

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
# ENDPOINT: RESUME ANALYSIS
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
        return {"error": "Unable to extract text"}

    # Scoring logic
    cleaned_resume = clean_text(resume_text)
    resume_vec = vectorizer.transform([cleaned_resume])
    text_to_compare = description if description.strip() else role
    desc_vec = vectorizer.transform([clean_text(text_to_compare)])
    
    predicted_category = model.predict(resume_vec)[0]
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    match_score = similarity * 100

    # FIX: Stricter Prompt to prevent blank fields
    prompt = f"""
    You are a professional ATS expert. Analyze this resume for {role} at {company}.
    Provide feedback in this EXACT format. Do not use bolding (**), do not add intro text.
    
    Strengths:
    - [item]
    
    Weaknesses:
    - [item]
    
    Improvement Areas:
    - [item]
    
    Actionable Suggestions:
    - [item]

    Resume:
    {resume_text[:2000]}
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "You are a strict technical recruiter. Output plain text sections only."},
                  {"role": "user", "content": prompt}],
        temperature=0.2 # Lower temperature = more consistent formatting
    )

    return {
        "company": company,
        "job_role": role,
        "predicted_category": predicted_category,
        "match_score": round(match_score, 2),
        "analysis": response.choices[0].message.content
    }

# ======================================================
# ENDPOINT: STUDY PLAN
# ======================================================
@app.post("/study-plan")
async def create_study_plan(data: StudyPlanRequest):
    prompt = f"""
    Create a {data.planFormat} roadmap for {data.targetRole} at {data.targetCompany}.
    Time: {data.timeline}, {data.dailyHours}/day. Style: {data.learningStyle}.
    Challenge: {data.challenges}.
    Based on this resume context: {data.resumeAnalysis}
    Output in clean Markdown.
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return {"study_plan": response.choices[0].message.content}
