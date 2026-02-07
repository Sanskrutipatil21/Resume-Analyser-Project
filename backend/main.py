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
# APP SETUP
# ======================================================
app = FastAPI(title="AI Resume & Study Planner")

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
# DATA MODELS FOR STUDY PLAN
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
# ENDPOINT 1: RESUME ANALYSIS (CLEANED PROMPT)
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
        return {"error": "Could not read resume"}

    # Scoring Logic
    cleaned_resume = clean_text(resume_text)
    resume_vec = vectorizer.transform([cleaned_resume])
    text_to_compare = description if description.strip() else role
    desc_vec = vectorizer.transform([clean_text(text_to_compare)])
    
    predicted_category = model.predict(resume_vec)[0]
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    match_score = similarity * 100

    # Cleaned AI Analysis Prompt to prevent "Disturbed" feedback
    prompt = f"""
    Analyze this resume for the role of {role} at {company}.
    Provide the feedback strictly using these headers and bullet points:

    Strengths:
    - (Point 1)
    
    Weaknesses:
    - (Point 1)
    
    Improvement Areas:
    - (Point 1)
    
    Actionable Suggestions:
    - (Point 1)

    Resume Content:
    {resume_text[:2000]}
    """
    
    ai_response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "You are a professional ATS resume reviewer."},
                  {"role": "user", "content": prompt}],
        temperature=0.3
    )

    return {
        "company": company,
        "job_role": role,
        "predicted_category": predicted_category,
        "match_score": round(match_score, 2),
        "analysis": ai_response.choices[0].message.content
    }

# ======================================================
# ENDPOINT 2: STUDY PLAN (NEW)
# ======================================================
@app.post("/study-plan")
async def create_study_plan(data: StudyPlanRequest):
    plan_prompt = f"""
    Create a highly detailed {data.planFormat} study roadmap for {data.targetRole} at {data.targetCompany}.
    The user can study {data.dailyHours} per day for {data.timeline}.
    Preferred Style: {data.learningStyle}. 
    Biggest Challenge: {data.challenges}.
    
    Base the plan on this Resume Analysis:
    {data.resumeAnalysis}
    
    Return the plan in beautiful Markdown format.
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "You are an expert technical mentor."},
                  {"role": "user", "content": plan_prompt}],
        temperature=0.5
    )
    
    return {"study_plan": response.choices[0].message.content}
