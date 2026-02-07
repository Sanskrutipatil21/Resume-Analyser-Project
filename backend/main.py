

import io
import re
import os
import pickle
import json
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from docx import Document
from groq import Groq
from sklearn.metrics.pairwise import cosine_similarity

# ======================================================
# APP SETUP
# ======================================================
app = FastAPI(title="AI Resume Feedback System")

# Enable CORS so your frontend can communicate with this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# LOAD ML MODELS
# ======================================================
# Ensure these files are in your project folder
model = pickle.load(open("resume_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# Initialize Groq Client (Ensure GROQ_API_KEY is set in your Environment Variables)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ======================================================
# HELPERS
# ======================================================
def clean_text(text: str) -> str:
    """Standardizes text for ML processing."""
    text = text.lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_text(file: UploadFile) -> str:
    """Extracts text from PDF or DOCX files."""
    content = file.file.read()
    if file.filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return " ".join(page.extract_text() or "" for page in reader.pages)
    if file.filename.lower().endswith(".docx"):
        doc = Document(io.BytesIO(content))
        return " ".join(p.text for p in doc.paragraphs)
    return ""

def get_ai_analysis(resume_text: str, company: str, role: str):
    """
    Asks Groq to analyze the resume and return a structured JSON object.
    This structure maps directly to your UI boxes (Strengths, Weaknesses, etc.)
    """
    resume_text = resume_text[:1800] # Limit text to stay within token limits
    
    prompt = f"""
    Analyze the following resume for the position of {role} at {company}.
    You MUST return ONLY a JSON object with these exact keys:
    "strengths": "Short bullet points of strengths",
    "weaknesses": "Short bullet points of weaknesses",
    "improvement_areas": "Specific skills or keywords missing",
    "suggestions": "Actionable advice for the candidate"

    Resume Content: {resume_text}
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a specialized ATS and Resume Analyst. Respond only in JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    return json.loads(response.choices[0].message.content)

# ======================================================
# ANALYSIS ENDPOINT
# ======================================================
@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    # 1. Extract and Clean Text
    resume_text = extract_text(resume)
    if not resume_text.strip():
        return {"error": "Unable to extract text from resume"}

    cleaned_resume = clean_text(resume_text)
    
    # 2. Vectorize for ML and Similarity
    resume_vec = vectorizer.transform([cleaned_resume])
    
    # 3. Predict Job Category
    predicted_category = model.predict(resume_vec)[0]

    # 4. Calculate Match Score using Cosine Similarity
    target_text = clean_text(description if description.strip() else role)
    desc_vec = vectorizer.transform([target_text])
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    match_score = similarity * 100

    # 5. Get Structured Feedback for UI Boxes
    # This prevents the boxes from being empty
    feedback_data = get_ai_analysis(resume_text, company, role)

    return {
        "company": company,
        "job_role": role,
        "predicted_category": predicted_category,
        "match_score": round(match_score, 2),
        "feedback": feedback_data  # Contains strengths, weaknesses, etc.
    }
