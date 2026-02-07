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

app = FastAPI(title="AI Resume Analyzer")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load ML Models
try:
    model = pickle.load(open("resume_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except Exception as e:
    print(f"Error loading models: {e}")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def clean_text(text: str) -> str:
    text = str(text).lower()
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

@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    try:
        raw_text = extract_text(resume)
        if not raw_text.strip():
            return {"error": "Could not read resume text"}

        cleaned_resume = clean_text(raw_text)
        target_text = clean_text(description if description.strip() else role)

        # 1. ML SCORING (Cosine Similarity)
        res_vec = vectorizer.transform([cleaned_resume])
        target_vec = vectorizer.transform([target_text])
        score = cosine_similarity(res_vec, target_vec)[0][0] * 100

        # 2. FIX FOR 0% ISSUE (Keyword Fallback)
        if score < 2:
            res_words = set(cleaned_resume.split())
            job_words = set(target_text.split())
            matches = res_words.intersection(job_words)
            if job_words:
                score = (len(matches) / len(job_words)) * 100

        # 3. AI ANALYSIS
        prompt = f"""
        Analyze this resume for the role '{role}' at '{company}'.
        Format the output EXACTLY like this:
        Strengths: (list items)
        Weaknesses: (list items)
        Improvement Areas: (list items)
        Actionable Suggestions: (list items)
        
        Resume: {raw_text[:2000]}
        """
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        analysis = response.choices[0].message.content

        # RETURN KEYS - These must match the result.html variable names
        return {
            "company": company,
            "job_role": role,
            "score": round(score, 2),
            "analysis": analysis
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
