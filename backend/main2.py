from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os

# --- Groq API Key ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request body model ---
class StudyPlanRequest(BaseModel):
    resumeAnalysis: str
    targetRole: str
    targetCompany: str
    timeline: str
    dailyHours: str
    skillLevel: str
    skillsToImprove: str
    learningStyle: str
    studyPreference: str
    biggestChallenge: str
    planFormat: str

# --- POST endpoint ---
@app.post("/study-plan")
async def generate_study_plan(request: StudyPlanRequest):
    prompt = f"""
You are a smart AI career coach. 
Generate a detailed study plan for a user based on the following information:

Resume Analysis:
{request.resumeAnalysis}

Target Role: {request.targetRole}
Target Company / Type: {request.targetCompany}
Timeline: {request.timeline}
Daily Study Hours: {request.dailyHours}
Current Skill Level: {request.skillLevel}
Skills to Improve: {request.skillsToImprove}
Learning Style: {request.learningStyle}
Study Preference: {request.studyPreference}
Biggest Challenge: {request.biggestChallenge}
Preferred Plan Format: {request.planFormat}

Return a clean study plan in steps or bullet points, suitable for front-end display.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Same model as main.py
            messages=[{"role":"user", "content":prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        study_plan = response.choices[0].message.content.strip()
        return {"study_plan": study_plan}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
