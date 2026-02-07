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
app = FastAPI(title="AI Resume Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# SAFE MODEL LOADING
# ======================================================
try:
    model = pickle.load(open("resume_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except Exception as e:
    print(f"[Warning] Could not load models: {e}")
    model = None
    vectorizer = None

# ======================================================
# GROQ CLIENT
# ======================================================
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
    try:
        content = file.file.read()
        if file.filename.lower().endswith(".pdf"):
            reader = PdfReader(io.BytesIO(content))
            return " ".join(page.extract_text() or "" for page in reader.pages)
        if file.filename.lower().endswith(".docx"):
            doc = Document(io.BytesIO(content))
            return " ".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"[Error] Failed to read file: {e}")
    return ""

def get_ai_analysis(resume_text: str, company: str, role: str) -> str:
    """Generates AI analysis using Groq (GROQ API)."""
    resume_text = resume_text[:1800]  # limit to first 1800 chars
    prompt = f"""
You are a senior ATS resume evaluator.
Analyze ONLY the resume below.
Return strictly in this format:

Strengths:
- ...
Weaknesses:
- ...
Improvement Areas:
- ...
Actionable Suggestions:
- ...

Target Company: {company}
Target Role: {role}

Resume:
{resume_text}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert resume analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=450
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Warning] AI analysis failed: {e}")
        return "AI analysis not available."

# ======================================================
# API ENDPOINT
# ======================================================
@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    # Extract text
    resume_text = extract_text(resume)
    if not resume_text.strip():
        return {"error": "Unable to extract resume text"}

    # -------- SCORE CALCULATION --------
    score = 0.0
    predicted_category = "Unknown"

    if vectorizer and model:
        try:
            cleaned_resume = clean_text(resume_text)
            resume_vec = vectorizer.transform([cleaned_resume])

            # Use description if provided; else role
            text_to_compare = description if description.strip() else role
            desc_vec = vectorizer.transform([clean_text(text_to_compare)])

            # Predict category
            predicted_category = model.predict(resume_vec)[0]

            # Cosine similarity
            similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
            score = similarity * 100

            # Fallback: ML confidence if similarity too low
            if score < 10:
                proba = model.predict_proba(resume_vec)[0]
                ml_conf = max(proba) * 100
                score = max(score, ml_conf * 0.5)

        except Exception as e:
            print(f"[Warning] Scoring failed: {e}")
            score = 0.0

    # Ensure score is 0-100
    score = min(max(round(score, 2), 0), 100)

    # -------- AI ANALYSIS --------
    analysis = get_ai_analysis(resume_text, company, role)

    # -------- RETURN --------
    return {
        "company": company,
        "job_role": role,
        "predicted_category": predicted_category,
        "score": score,          # Frontend-friendly
        "analysis": analysis
    }

# ======================================================
# RUN SERVER
# ======================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
