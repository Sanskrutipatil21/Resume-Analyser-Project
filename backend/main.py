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

# ======================================================
# APP CONFIGURATION
# ======================================================
app = FastAPI(title="AI Resume Analyzer")

# Allowing Frontend to communicate with Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# LOAD ML MODELS
# ======================================================
try:
    # Loading the files you provided
    model = pickle.load(open("resume_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except Exception as e:
    print(f"CRITICAL ERROR: Could not load pkl files. {e}")

# Initialize Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ======================================================
# HELPERS
# ======================================================
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

def get_ai_analysis(resume_text: str, company: str, role: str) -> str:
    # Limit text to avoid token limits
    resume_text = resume_text[:1800]
    prompt = f"""
    You are a senior ATS resume evaluator. Analyze the resume for {role} at {company}.
    Format your response EXACTLY as follows:
    
    Strengths:
    - (point)
    Weaknesses:
    - (point)
    Improvement Areas:
    - (point)
    Actionable Suggestions:
    - (point)

    Resume Content: {resume_text}
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

# ======================================================
# MAIN API ENDPOINT
# ======================================================
@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    try:
        resume_full_text = extract_text(resume)
        if not resume_full_text.strip():
            return {"error": "Could not extract text from the file"}

        # 1. Clean and Vectorize
        cleaned_resume = clean_text(resume_full_text)
        resume_vec = vectorizer.transform([cleaned_resume])
        
        # If user didn't provide desc, use the role name
        target_text = clean_text(description if description.strip() else role)
        desc_vec = vectorizer.transform([target_text])

        # 2. Calculate ML Match Score (Cosine Similarity)
        similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
        final_score = similarity * 100

        # --- FIX FOR 0% ISSUE ---
        # If the ML vectorizer doesn't recognize the words, we manually count matching words
        if final_score < 1:
            resume_words = set(cleaned_resume.split())
            job_words = set(target_text.split())
            common = resume_words.intersection(job_set)
            if job_words:
                # Basic overlap percentage as a fallback
                final_score = (len(common) / len(job_words)) * 100
            else:
                # If no role provided, we can't score
                final_score = 0

        # 3. Get AI Feedback
        analysis = get_ai_analysis(resume_full_text, company, role)

        # 4. Return Data (Keys are mapped to match result.html)
        return {
            "company": company,
            "job_role": role,
            "score": round(final_score, 2),
            "analysis": analysis
        }

    except Exception as e:
        print(f"Internal Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
