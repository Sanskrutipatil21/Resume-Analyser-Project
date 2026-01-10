# ml_model.py
import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LogisticRegression
import pickle


def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

ROLE_SKILLS = {
    "Backend Developer": {
        "python": 3,
        "api": 3,
        "sql": 2,
        "database": 2,
        "django": 2,
        "flask": 2,
        "docker": 1,
        "git": 1
    },
    "Data Analyst": {
        "sql": 3,
        "pandas": 3,
        "excel": 2,
        "python": 2,
        "data visualization": 2,
        "machine learning": 1,
        "statistics": 1
    },
    "Android Developer": {
        "kotlin": 3,
        "java": 3,
        "android": 3,
        "firebase": 2,
        "api": 2,
        "ui": 1
    }
}

import random

FEEDBACK_TEMPLATES = {
    "matched_skill": [
        "Your experience with {skill} aligns well with the {role} role.",
        "{skill} is a strong skill match for the {role} position.",
        "Having {skill} strengthens your profile for a {role} role."
    ],
    "missing_skill": [
        "For a {role} role, {skill} is an important expectation but was not found.",
        "{skill} is commonly required for {role} positions and seems missing.",
        "Your resume does not mention {skill}, which recruiters often expect for {role}."
    ]
}


class ResumeMLAnalyzer:
    def __init__(self, dataset_path="dataset.csv"):
        # Load dataset
        self.data = pd.read_csv(dataset_path)

        # Combine resume text + job role for training
        self.data["combined"] = (
            self.data["resume_text"] + " " + self.data["job_role"]
        )

        # Create TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(stop_words="english")

        # Train TF-IDF model
        self.tfidf_matrix = self.vectorizer.fit_transform(
            self.data["combined"]
        )

    def calculate_match_score(self, resume_text, job_role):
        user_input = resume_text + " " + job_role

        user_vector = self.vectorizer.transform([user_input])

        similarity_scores = cosine_similarity(
            user_vector, self.tfidf_matrix
        )

        best_score = similarity_scores.max()

        # Convert to percentage
        return round(best_score * 100, 2)
    
def analyze_resume_role_based(resume_text: str, job_role: str):
    resume_text = resume_text.lower()

    role_data = ROLE_SKILLS.get(job_role, {})
    strengths = []
    weaknesses = []

    matched_weight = 0
    total_weight = sum(role_data.values())

    for skill, weight in role_data.items():
        if skill in resume_text:
            matched_weight += weight
            strengths.append(
                random.choice(FEEDBACK_TEMPLATES["matched_skill"])
                .format(skill=skill.title(), role=job_role)
            )
        else:
            weaknesses.append(
                random.choice(FEEDBACK_TEMPLATES["missing_skill"])
                .format(skill=skill.title(), role=job_role)
            )

    match_score = int((matched_weight / total_weight) * 100) if total_weight else 0

    return {
        "match_score": match_score,
        "strengths": strengths[:4],
        "weaknesses": weaknesses[:4]
    }

    import pandas as pd

df = pd.read_csv("dataset.csv")
df["clean_resume"] = df["Resume"].apply(clean_text)
vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=5000
)

X = vectorizer.fit_transform(df["clean_resume"])
y = df["Category"]

#print(df.columns)
#print(df.head(2))


model = LogisticRegression(max_iter=1000)
model.fit(X, y)

# Save model and vectorizer
pickle.dump(model, open("resume_model.pkl", "wb"))
pickle.dump(vectorizer, open("vectorizer.pkl", "wb"))

