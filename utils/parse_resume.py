import os
from dotenv import load_dotenv
import pdfplumber
from docx import Document
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType

load_dotenv()

EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

async def parse_resume_with_ai(file_path: str, mime_type: str):
    """
    Parse resume using AI to extract skills, education, and experience
    """
    
    # First extract text using traditional methods
    text = ""
    if mime_type == "application/pdf":
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
    
    # Use Gemini with file attachment for better parsing
    try:
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"resume_parse_{os.path.basename(file_path)}",
            system_message="You are an expert resume parser. Extract skills, education, and experience from resumes."
        ).with_model("gemini", "gemini-2.0-flash")
        
        file_content = FileContentWithMimeType(
            file_path=file_path,
            mime_type=mime_type
        )
        
        prompt = """Extract the following information from this resume:
1. Skills (technical and soft skills as a comma-separated list)
2. Education (degrees, institutions, years)
3. Experience (companies, roles, duration)
4. Overall summary

Provide the output in this exact format:
SKILLS: skill1, skill2, skill3, ...
EDUCATION: education details
EXPERIENCE: experience details
SUMMARY: brief summary"""
        
        user_message = UserMessage(
            text=prompt,
            file_contents=[file_content]
        )
        
        response = await chat.send_message(user_message)
        
        # Parse AI response
        skills = []
        education = ""
        experience = ""
        summary = ""
        
        for line in response.split('\n'):
            if line.startswith('SKILLS:'):
                skills_text = line.replace('SKILLS:', '').strip()
                skills = [s.strip() for s in skills_text.split(',') if s.strip()]
            elif line.startswith('EDUCATION:'):
                education = line.replace('EDUCATION:', '').strip()
            elif line.startswith('EXPERIENCE:'):
                experience = line.replace('EXPERIENCE:', '').strip()
            elif line.startswith('SUMMARY:'):
                summary = line.replace('SUMMARY:', '').strip()
        
        return {
            "text": text,
            "skills": skills,
            "education": education,
            "experience": experience,
            "summary": summary
        }
    
    except Exception as e:
        # Fallback to basic text extraction
        print(f"AI parsing failed: {str(e)}, using basic extraction")
        
        # Simple skill extraction from text
        common_skills = [
            "Python", "Java", "JavaScript", "C++", "React", "Angular", "Vue",
            "Node.js", "Django", "Flask", "FastAPI", "SQL", "MongoDB", "PostgreSQL",
            "AWS", "Azure", "Docker", "Kubernetes", "Git", "Machine Learning",
            "Data Science", "HTML", "CSS", "TypeScript", "Communication", "Leadership"
        ]
        
        found_skills = [skill for skill in common_skills if skill.lower() in text.lower()]
        
        return {
            "text": text,
            "skills": found_skills,
            "education": "Not extracted",
            "experience": "Not extracted",
            "summary": text[:200] if len(text) > 200 else text
        }
