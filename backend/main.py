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
from sklearn.feature_extraction.text import TfidfVectorizer
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
except:
    # fallback: simple TF-IDF if pickle fails
    vectorizer = TfidfVectorizer()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def clean_text(text: str) -> str:
    text = text.lower()
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

@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    try:
        raw_text = extract_text(resume)
        cleaned_res = clean_text(raw_text)
        
        # Use role + description as target
        target_text = clean_text(f"{role} {description}")
        
        # VECTORIZE
        vecs = vectorizer.fit_transform([cleaned_res, target_text])
        score = cosine_similarity(vecs[0], vecs[1])[0][0] * 100
        
        # fallback keyword match if similarity is too low
        if score < 5:
            res_words = set(cleaned_res.split())
            target_words = set(target_text.split())
            matches = res_words.intersection(target_words)
            if target_words:
                score = (len(matches) / len(target_words)) * 100
        
        score = round(min(score, 100), 2)

        # AI Analysis
        prompt = f"Analyze this resume for {role} at {company}. Provide Strengths, Weaknesses, Improvement Areas, and Actionable Suggestions. Resume: {raw_text[:1500]}"
        ai_res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        analysis = ai_res.choices[0].message.content

        return {
            "company": company,
            "job_role": role,
            "score": score,
            "analysis": analysis
        }
    except Exception as e:
        print(f"Server Error: {e}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
