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

# --- APP SETUP ---
app = FastAPI(title="AI Resume Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOAD ML MODELS ---
model = pickle.load(open("resume_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- HELPERS ---
def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_text(file: UploadFile) -> str:
    content = file.file.read()
    if file.filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return " ".join(page.extract_text() or "" for page in reader.pages)
    if file.filename.lower().endswith(".docx"):
        doc = Document(io.BytesIO(content))
        return " ".join(p.text for p in doc.paragraphs)
    return ""

def get_ai_analysis(resume_text: str, company: str, role: str):
    """Returns structured JSON for the UI boxes."""
    resume_text = resume_text[:1800]
    prompt = f"""
    Analyze the resume for {role} at {company}.
    Return ONLY a JSON object with these keys:
    "strengths": ["point 1", "point 2"],
    "weaknesses": ["point 1", "point 2"],
    "improvement_areas": ["point 1", "point 2"],
    "suggestions": ["point 1", "point 2"]
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.4
    )
    return json.loads(response.choices[0].message.content)

# --- ENDPOINT ---
@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    resume_text = extract_text(resume)
    if not resume_text.strip(): return {"error": "Empty resume"}

    # Scoring Logic
    cleaned_resume = clean_text(resume_text)
    resume_vec = vectorizer.transform([cleaned_resume])
    target_text = description if description.strip() else role
    desc_vec = vectorizer.transform([clean_text(target_text)])
    
    match_score = cosine_similarity(resume_vec, desc_vec)[0][0] * 100
    predicted_category = model.predict(resume_vec)[0]

    # Feedback Logic
    feedback = get_ai_analysis(resume_text, company, role)

    return {
        "match_score": round(match_score, 2),
        "predicted_category": predicted_category,
        "feedback": feedback
    }
