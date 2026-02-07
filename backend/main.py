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
# APP SETUP
# ======================================================
app = FastAPI(title="AI Resume Feedback System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load your local ML models
model = pickle.load(open("resume_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ======================================================
# HELPERS
# ======================================================
def clean_text(text: str) -> str:
    text = text.lower()
    # Keep alphanumeric characters to improve matching score
    text = re.sub(r"[^a-z0-9\s]", " ", text)
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

def get_ai_analysis(resume_text: str, company: str, role: str) -> str:
    # We use a very strict prompt to ensure the frontend can parse the sections
    prompt = f"""
    Analyze the resume for the role of {role} at {company}.
    You MUST return the response strictly in this format without any bolding or introduction:

    Strengths:
    - [item]
    
    Weaknesses:
    - [item]
    
    Improvement Areas:
    - [item]
    
    Actionable Suggestions:
    - [item]

    Resume Content:
    {resume_text[:2000]}
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a professional ATS. Output plain text headers only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2 # Low temperature ensures the AI follows the format strictly
    )
    return response.choices[0].message.content.strip()

# ======================================================
# MAIN ANALYSIS ENDPOINT
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
        return {"error": "Could not read resume file"}

    # 1. Vectorize and Calculate Initial Similarity
    cleaned_resume = clean_text(resume_text)
    text_to_compare = clean_text(description if description.strip() else role)
    
    resume_vec = vectorizer.transform([cleaned_resume])
    desc_vec = vectorizer.transform([text_to_compare])
    
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    match_score = similarity * 100

    # 2. SCORE FIX: Fallback to Keyword Overlap if ML similarity is 0
    # This prevents the "0% Score" error for unusual resumes
    if match_score < 5:
        res_words = set(cleaned_resume.split())
        desc_words = set(text_to_compare.split())
        if desc_words:
            overlap = len(res_words.intersection(desc_words)) / len(desc_words)
            match_score = overlap * 100

    # 3. Predict Category using your Pickle model
    predicted_category = model.predict(resume_vec)[0]

    # 4. Get AI Analysis (Feedback)
    analysis = get_ai_analysis(resume_text, company, role)

    return {
        "company": company,
        "job_role": role,
        "predicted_category": predicted_category,
        "match_score": round(match_score, 2),
        "analysis": analysis
    }
