import io
import re
import os
import pickle
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from docx import Document
from groq import Groq

app = FastAPI(title="AI Resume Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
        resume_text = extract_text(resume)
        
        # PROMPT: Asking AI for the percentage
        prompt = f"""
        You are an ATS Expert. Analyze this resume for the role '{role}' at '{company}'.
        
        Provide the output in this EXACT format:
        Match Score: [Insert a number between 0-100]%
        Strengths: (bullet points)
        Weaknesses: (bullet points)
        Improvement Areas: (bullet points)
        Actionable Suggestions: (bullet points)
        
        Resume Content: {resume_text[:2000]}
        """
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        full_analysis = response.choices[0].message.content

        # EXTRACT PERCENTAGE FROM AI TEXT
        # Searches for "Match Score: 85%" and extracts "85"
        ai_score = 0
        match = re.search(r"Match Score:\s*(\d+)", full_analysis)
        if match:
            ai_score = int(match.group(1))

        return {
            "company": company,
            "job_role": role,
            "score": ai_score,  # Now using the AI's calculated score
            "analysis": full_analysis
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
