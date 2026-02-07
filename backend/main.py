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
# APP INITIALIZATION
# ======================================================
app = FastAPI(title="AI Resume Feedback System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Local Models (Ensure these .pkl files are in your directory)
try:
    model = pickle.load(open("resume_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except FileNotFoundError:
    print("Warning: .pkl files not found. Ensure models are in the root directory.")

# Groq Client setup
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ======================================================
# HELPER FUNCTIONS
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

def get_ai_analysis(resume_text: str, company: str, role: str) -> str:
    """Sends resume content to Groq for detailed feedback."""
    # Truncate text to stay within token limits
    resume_text = resume_text[:1800]
    prompt = f"""
    Analyze the following resume content for the position of {role} at {company}.
    Provide a detailed evaluation under these specific headings:
    1. Strengths
    2. Weaknesses
    3. Areas of Improvement
    4. Actionable Suggestions

    Resume Content: {resume_text}
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a professional HR and ATS analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()

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
    # 1. Text Extraction
    resume_text = extract_text(resume)
    if not resume_text.strip():
        return {"error": "Could not extract text from the uploaded file."}

    # 2. Text Vectorization
    cleaned_resume = clean_text(resume_text)
    resume_vec = vectorizer.transform([cleaned_resume])
    
    # 3. Predict Category (using your ML model)
    predicted_category = model.predict(resume_vec)[0]

    # 4. Calculate Match Score (Cosine Similarity)
    # Compare resume against Job Description (or Role name if JD is empty)
    text_to_compare = description if description.strip() else role
    desc_vec = vectorizer.transform([clean_text(text_to_compare)])
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    match_score = similarity * 100

    # 5. Get AI Feedback (using Groq)
    analysis_feedback = get_ai_analysis(resume_text, company, role)

    return {
        "company": company,
        "job_role": role,
        "predicted_category": predicted_category,
        "match_score": round(match_score, 2),
        "analysis": analysis_feedback
    }
