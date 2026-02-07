from sklearn.metrics.pairwise import cosine_similarity

@app.post("/analyze")
async def analyze_resume(
    resume: UploadFile = File(...),
    company: str = Form(...),
    role: str = Form(...),
    description: str = Form("") # This is the job description from your frontend
):
    resume_text = extract_text(resume)
    if not resume_text.strip():
        return {"error": "Unable to extract resume text"}

    # 1. Clean and Vectorize the Resume
    cleaned_resume = clean_text(resume_text)
    resume_vec = vectorizer.transform([cleaned_resume])

    # 2. Clean and Vectorize the Job Description
    cleaned_desc = clean_text(description)
    desc_vec = vectorizer.transform([cleaned_desc])

    # 3. Calculate Category (using your existing model)
    predicted_category = model.predict(resume_vec)[0]

    # 4. Calculate actual Match Score using Cosine Similarity
    # This measures how similar the resume is to the job description
    similarity = cosine_similarity(resume_vec, desc_vec)[0][0]
    
    # If the description is empty, fallback to the model's confidence 
    # or a default value to avoid 0%
    if not description.strip():
        match_score = max(model.predict_proba(resume_vec)[0]) * 100
    else:
        match_score = similarity * 100

    # -------- AI ANALYSIS (GROQ) --------
    analysis = get_ai_analysis(resume_text, company, role)

    return {
        "company": company,
        "job_role": role,
        "predicted_category": predicted_category,
        "match_score": round(match_score, 2),
        "analysis": analysis
    }
