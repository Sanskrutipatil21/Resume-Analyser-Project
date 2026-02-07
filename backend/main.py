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
try:
    model = pickle.load(open("resume_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except Exception as e:
    print(f"Model Load Error: {e}")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
    prompt = f"""
    You are an expert ATS System. Analyze this resume for the role: {role} at {company}.
    Provide the output in this exact format:
    Strengths:
    - point 1
    Weaknesses:
    - point 1
    Improvement Areas:
    - point 1
    Actionable Suggestions:
    - point 1
    
    Resume: {resume_text[:2000]}
    """
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    try:
        resume_raw = extract_text(resume)
        cleaned_resume = clean_text(resume_raw)
        
        # 1. ML Scoring
        resume_vec = vectorizer.transform([cleaned_resume])
        target_text = clean_text(description if description.strip() else role)
        desc_vec = vectorizer.transform([target_text])
        
        similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
        final_score = similarity * 100

        # --- FIX FOR 0% SCORE (Keyword Fallback) ---
        if final_score < 1:
            res_words = set(cleaned_resume.split())
            job_words = set(target_text.split())
            common = res_words.intersection(job_words)
            if job_words:
                final_score = (len(common) / len(job_words)) * 100

        # 2. AI Analysis
        analysis = get_ai_analysis(resume_raw, company, role)

        # Keys matched to result.html: score, analysis, company, job_role
        return {
            "company": company,
            "job_role": role,
            "score": round(final_score, 2),
            "analysis": analysis
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
