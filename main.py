import io
import re
import pickle
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from docx import Document

app = FastAPI(title="ML Resume Analyzer")

# ------------------ CORS ------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Load trained ML ------------------
model = pickle.load(open("resume_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# ------------------ Text cleaning ------------------
def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ------------------ API ------------------
@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("")
):
    # 1. Read uploaded file
    file_bytes = await resume.read()
    resume_text = ""

    # 2. PDF
    if resume.content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            if page.extract_text():
                resume_text += page.extract_text() + "\n"

    # 3. DOC / DOCX
    elif resume.content_type in [
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]:
        doc = Document(io.BytesIO(file_bytes))
        for para in doc.paragraphs:
            resume_text += para.text + "\n"

    else:
        return {"error": "Unsupported file type. Upload PDF, DOC, or DOCX only."}

    if not resume_text.strip():
        return {"error": "Could not extract text from resume"}

    # 4. CLEAN + VECTORIZE
    cleaned = clean_text(resume_text)
    vectorized = vectorizer.transform([cleaned])

    # 5. ML prediction
    predicted_category = model.predict(vectorized)[0]
    ml_confidence = max(model.predict_proba(vectorized)[0]) * 100

    # 6. ROLE MATCH SCORE (this makes score CHANGE)
    role_clean = clean_text(role)
    resume_words = set(cleaned.split())
    role_words = set(role_clean.split())

    overlap = resume_words.intersection(role_words)
    role_match_score = (len(overlap) / max(len(role_words), 1)) * 100

    # 7. FINAL job-fit score
    final_score = (0.4 * ml_confidence) + (0.6 * role_match_score)

    # 8. Strengths / weaknesses
    strengths = []
    weaknesses = []

    if final_score > 75:
        strengths.append("Resume strongly matches the target role")
    else:
        weaknesses.append("Resume could be better aligned with the job role")

    if len(resume_text.split()) < 300:
        weaknesses.append("Resume content is too short")

    # 9. Response
    return {
        "company": company,
        "job_role": role,
        "predicted_category": predicted_category,
        "match_score": round(final_score, 2),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "improvement_areas": [],
        "actionable_suggestions": []
    }
