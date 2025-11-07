from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

async def score_resume(
    resume_text: str,
    student_skills: list,
    student_cgpa: float,
    job_description: str,
    required_skills: list,
    min_cgpa: float
) -> float:
    """
    Score resume using TF-IDF + Cosine Similarity + CGPA weighting
    """
    
    # Text similarity score (60% weight)
    text_score = 0
    if resume_text and job_description:
        try:
            vectorizer = TfidfVectorizer()
            vectors = vectorizer.fit_transform([resume_text, job_description])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            text_score = similarity * 60
        except:
            text_score = 0
    
    # Skills match score (30% weight)
    skills_score = 0
    if required_skills and student_skills:
        matched_skills = set([s.lower() for s in student_skills]) & set([s.lower() for s in required_skills])
        skills_score = (len(matched_skills) / len(required_skills)) * 30 if len(required_skills) > 0 else 0
    
    # CGPA score (10% weight)
    cgpa_score = 0
    if student_cgpa >= min_cgpa:
        # Normalize CGPA to 0-10 scale
        cgpa_normalized = (student_cgpa / 10.0) * 10
        cgpa_score = cgpa_normalized
    else:
        # Penalty for not meeting minimum CGPA
        cgpa_score = (student_cgpa / min_cgpa) * 5 if min_cgpa > 0 else 0
    
    total_score = text_score + skills_score + cgpa_score
    
    # Normalize to 0-100
    return round(min(100, max(0, total_score)), 2)
