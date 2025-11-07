from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import io

from utils.parse_resume import parse_resume_with_ai
from utils.score_resume import score_resume
from utils.send_email import send_email
from utils.generate_report import generate_excel_report
from utils.generate_pdf_report import generate_student_performance_pdf, generate_student_list_pdf

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
JWT_SECRET = os.environ.get('JWT_SECRET', 'secret_key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = timedelta(days=30)

# Security
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ======================== MODELS ========================

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str  # student, hod, tpo

class UserRegister(UserBase):
    password: str
    department: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    department: Optional[str] = None
    is_approved: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StudentProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    roll_number: str
    cgpa: float
    skills: List[str] = []
    resume_url: Optional[str] = None
    resume_text: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Drive(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    role: str
    description: str
    min_cgpa: float
    required_skills: List[str] = []
    eligible_departments: List[str] = []
    deadline: datetime
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Application(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    drive_id: str
    student_id: str
    status: str = "Applied"  # Applied, Shortlisted, Selected, Rejected
    ai_score: Optional[float] = None
    current_round: str = "Applied"  # Applied, Aptitude, Coding, Group Discussion, HR, Selected, Rejected
    round_history: List[dict] = []
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PlacementHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    year: int
    department: str
    company_name: str
    role: str
    students_placed: int
    avg_package: float

# ======================== AUTH HELPERS ========================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + JWT_EXPIRATION
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(payload: dict = Depends(verify_token)):
    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

# ======================== AUTH ROUTES ========================

@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = pwd_context.hash(user_data.password)
    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        department=user_data.department,
        is_approved=user_data.role in ["hod", "tpo"]  # Auto-approve HOD/TPO
    )
    
    user_dict = user.model_dump()
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    user_dict['password'] = hashed_password
    
    await db.users.insert_one(user_dict)
    
    token = create_access_token({"user_id": user.id, "role": user.role})
    
    return {
        "token": token,
        "user": user.model_dump()
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not pwd_context.verify(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user['is_approved'] and user['role'] == 'student':
        raise HTTPException(status_code=403, detail="Account pending approval")
    
    token = create_access_token({"user_id": user['id'], "role": user['role']})
    
    user_obj = User(**user)
    return {
        "token": token,
        "user": user_obj.model_dump()
    }

@api_router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ======================== STUDENT ROUTES ========================

@api_router.post("/students/profile")
async def create_profile(profile_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can create profiles")
    
    profile = StudentProfile(
        user_id=current_user.id,
        roll_number=profile_data['roll_number'],
        cgpa=profile_data['cgpa'],
        skills=profile_data.get('skills', [])
    )
    
    profile_dict = profile.model_dump()
    profile_dict['updated_at'] = profile_dict['updated_at'].isoformat()
    
    await db.profiles.insert_one(profile_dict)
    
    return profile

@api_router.get("/students/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can view their profile")
    
    profile = await db.profiles.find_one({"user_id": current_user.id}, {"_id": 0})
    if not profile:
        return None
    
    return profile

@api_router.post("/students/resume")
async def upload_resume(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can upload resumes")
    
    # Validate file
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files allowed")
    
    # Read file
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    # Save file
    file_path = f"/tmp/{current_user.id}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Parse resume with AI
    try:
        resume_data = await parse_resume_with_ai(file_path, file.content_type)
        
        # Update profile
        await db.profiles.update_one(
            {"user_id": current_user.id},
            {"$set": {
                "resume_url": file.filename,
                "resume_text": resume_data['text'],
                "skills": list(set(resume_data.get('skills', []))),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "message": "Resume uploaded and parsed successfully",
            "extracted_data": resume_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing resume: {str(e)}")

# ======================== DRIVES ROUTES ========================

@api_router.get("/drives")
async def get_drives(current_user: User = Depends(get_current_user)):
    drives = await db.drives.find({}, {"_id": 0}).to_list(1000)
    return drives

@api_router.post("/drives")
async def create_drive(drive_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "tpo":
        raise HTTPException(status_code=403, detail="Only TPO can create drives")
    
    drive = Drive(
        company_name=drive_data['company_name'],
        role=drive_data['role'],
        description=drive_data['description'],
        min_cgpa=drive_data['min_cgpa'],
        required_skills=drive_data.get('required_skills', []),
        eligible_departments=drive_data.get('eligible_departments', []),
        deadline=datetime.fromisoformat(drive_data['deadline']),
        created_by=current_user.id
    )
    
    drive_dict = drive.model_dump()
    drive_dict['created_at'] = drive_dict['created_at'].isoformat()
    drive_dict['deadline'] = drive_dict['deadline'].isoformat()
    
    await db.drives.insert_one(drive_dict)
    
    return drive

@api_router.get("/drives/{drive_id}")
async def get_drive(drive_id: str, current_user: User = Depends(get_current_user)):
    drive = await db.drives.find_one({"id": drive_id}, {"_id": 0})
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    return drive

# ======================== APPLICATIONS ROUTES ========================

@api_router.post("/applications")
async def apply_to_drive(application_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can apply")
    
    # Check if already applied
    existing = await db.applications.find_one({
        "drive_id": application_data['drive_id'],
        "student_id": current_user.id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Already applied to this drive")
    
    # Get profile and drive
    profile = await db.profiles.find_one({"user_id": current_user.id}, {"_id": 0})
    drive = await db.drives.find_one({"id": application_data['drive_id']}, {"_id": 0})
    
    if not profile:
        raise HTTPException(status_code=400, detail="Please complete your profile first")
    
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    
    # Calculate AI score
    ai_score = await score_resume(
        profile.get('resume_text', ''),
        profile.get('skills', []),
        profile.get('cgpa', 0),
        drive['description'],
        drive['required_skills'],
        drive['min_cgpa']
    )
    
    application = Application(
        drive_id=application_data['drive_id'],
        student_id=current_user.id,
        ai_score=ai_score
    )
    
    app_dict = application.model_dump()
    app_dict['applied_at'] = app_dict['applied_at'].isoformat()
    
    await db.applications.insert_one(app_dict)
    
    return application

@api_router.get("/applications/my")
async def get_my_applications(current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can view their applications")
    
    applications = await db.applications.find({"student_id": current_user.id}, {"_id": 0}).to_list(1000)
    
    # Enrich with drive data
    for app in applications:
        drive = await db.drives.find_one({"id": app['drive_id']}, {"_id": 0})
        app['drive'] = drive
    
    return applications

@api_router.get("/applications/drive/{drive_id}")
async def get_drive_applications(drive_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["tpo", "hod"]:
        raise HTTPException(status_code=403, detail="Only TPO/HOD can view applications")
    
    applications = await db.applications.find({"drive_id": drive_id}, {"_id": 0}).to_list(1000)
    
    # Enrich with student data
    for app in applications:
        user = await db.users.find_one({"id": app['student_id']}, {"_id": 0})
        profile = await db.profiles.find_one({"user_id": app['student_id']}, {"_id": 0})
        app['student'] = user
        app['profile'] = profile
    
    # Sort by AI score
    applications.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
    
    return applications

# ======================== TPO ROUTES ========================

@api_router.post("/tpo/select-for-round")
async def select_for_round(selection_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "tpo":
        raise HTTPException(status_code=403, detail="Only TPO can select students")
    
    application_ids = selection_data['application_ids']
    next_round = selection_data['next_round']  # Aptitude, Coding, Group Discussion, HR, Selected
    drive_id = selection_data['drive_id']
    
    # Get drive details
    drive = await db.drives.find_one({"id": drive_id}, {"_id": 0})
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    
    selected_emails = []
    
    for app_id in application_ids:
        # Update application
        application = await db.applications.find_one({"id": app_id}, {"_id": 0})
        if application:
            round_update = {
                "round": next_round,
                "selected_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.applications.update_one(
                {"id": app_id},
                {
                    "$set": {"current_round": next_round},
                    "$push": {"round_history": round_update}
                }
            )
            
            # Get student email
            student = await db.users.find_one({"id": application['student_id']}, {"_id": 0})
            if student:
                selected_emails.append({
                    "email": student['email'],
                    "name": student['name']
                })
    
    # Send emails
    for student in selected_emails:
        try:
            if next_round == "Selected":
                subject = f"Congratulations! Selected for {drive['role']} at {drive['company_name']}"
                message = f"Dear {student['name']},\n\nCongratulations! You have been selected for the role of {drive['role']} at {drive['company_name']}.\n\nPlease contact the Training & Placement Office for further details.\n\nBest Regards,\nTraining & Placement Officer"
            else:
                subject = f"Selected for {next_round} Round - {drive['company_name']}"
                message = f"Dear {student['name']},\n\nCongratulations! You have been shortlisted for the {next_round} round for the role of {drive['role']} at {drive['company_name']}.\n\nPlease check your dashboard for further details and schedule.\n\nBest Regards,\nTraining & Placement Officer"
            
            await send_email(student['email'], subject, message)
        except Exception as e:
            logging.error(f"Error sending email to {student['email']}: {str(e)}")
    
    return {
        "message": f"Selected {len(application_ids)} students for {next_round}",
        "emails_sent": len(selected_emails)
    }

@api_router.post("/tpo/reject-applications")
async def reject_applications(rejection_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "tpo":
        raise HTTPException(status_code=403, detail="Only TPO can reject students")
    
    application_ids = rejection_data['application_ids']
    
    for app_id in application_ids:
        await db.applications.update_one(
            {"id": app_id},
            {"$set": {"current_round": "Rejected"}}
        )
    
    return {"message": f"Rejected {len(application_ids)} applications"}

# ======================== HOD ROUTES ========================

@api_router.get("/hod/pending-approvals")
async def get_pending_approvals(current_user: User = Depends(get_current_user)):
    if current_user.role != "hod":
        raise HTTPException(status_code=403, detail="Only HOD can view approvals")
    
    students = await db.users.find({
        "role": "student",
        "department": current_user.department,
        "is_approved": False
    }, {"_id": 0}).to_list(1000)
    
    return students

@api_router.post("/hod/approve-student/{student_id}")
async def approve_student(student_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "hod":
        raise HTTPException(status_code=403, detail="Only HOD can approve students")
    
    await db.users.update_one(
        {"id": student_id, "department": current_user.department},
        {"$set": {"is_approved": True}}
    )
    
    return {"message": "Student approved successfully"}

@api_router.get("/hod/statistics")
async def get_hod_statistics(current_user: User = Depends(get_current_user)):
    if current_user.role != "hod":
        raise HTTPException(status_code=403, detail="Only HOD can view statistics")
    
    # Get 5-year historical data
    history = await db.placement_history.find({
        "department": current_user.department
    }, {"_id": 0}).to_list(1000)
    
    # Current year stats
    current_year = datetime.now().year
    
    # Get all students in department
    total_students = await db.users.count_documents({
        "role": "student",
        "department": current_user.department,
        "is_approved": True
    })
    
    # Get placed students (Selected status)
    placed_apps = await db.applications.find({
        "current_round": "Selected"
    }, {"_id": 0}).to_list(1000)
    
    # Filter by department
    placed_students = []
    for app in placed_apps:
        student = await db.users.find_one({"id": app['student_id']}, {"_id": 0})
        if student and student.get('department') == current_user.department:
            placed_students.append(app)
    
    placement_percentage = (len(placed_students) / total_students * 100) if total_students > 0 else 0
    
    return {
        "department": current_user.department,
        "current_year": current_year,
        "total_students": total_students,
        "placed_students": len(placed_students),
        "placement_percentage": round(placement_percentage, 2),
        "historical_data": history
    }

@api_router.get("/hod/students")
async def get_department_students(current_user: User = Depends(get_current_user)):
    if current_user.role != "hod":
        raise HTTPException(status_code=403, detail="Only HOD can view students")
    
    # Get all students in department
    students = await db.users.find({
        "role": "student",
        "department": current_user.department
    }, {"_id": 0, "password": 0}).to_list(1000)
    
    # Enrich with profile data
    for student in students:
        profile = await db.profiles.find_one({"user_id": student['id']}, {"_id": 0})
        if profile:
            student['roll_number'] = profile.get('roll_number', 'N/A')
            student['cgpa'] = profile.get('cgpa', 'N/A')
            student['skills'] = profile.get('skills', [])
        else:
            student['roll_number'] = 'N/A'
            student['cgpa'] = 'N/A'
            student['skills'] = []
    
    return students

@api_router.put("/hod/students/{student_id}")
async def update_student(student_id: str, update_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "hod":
        raise HTTPException(status_code=403, detail="Only HOD can update students")
    
    # Verify student belongs to HOD's department
    student = await db.users.find_one({"id": student_id, "department": current_user.department}, {"_id": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found in your department")
    
    # Update user data
    user_updates = {}
    if 'name' in update_data:
        user_updates['name'] = update_data['name']
    if 'email' in update_data:
        user_updates['email'] = update_data['email']
    
    if user_updates:
        await db.users.update_one(
            {"id": student_id},
            {"$set": user_updates}
        )
    
    # Update profile data
    profile_updates = {}
    if 'roll_number' in update_data:
        profile_updates['roll_number'] = update_data['roll_number']
    if 'cgpa' in update_data:
        profile_updates['cgpa'] = float(update_data['cgpa'])
    if 'skills' in update_data:
        profile_updates['skills'] = update_data['skills']
    
    if profile_updates:
        profile_updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        await db.profiles.update_one(
            {"user_id": student_id},
            {"$set": profile_updates}
        )
    
    return {"message": "Student updated successfully"}

@api_router.get("/hod/statistics-2025")
async def get_2025_statistics(current_user: User = Depends(get_current_user)):
    if current_user.role != "hod":
        raise HTTPException(status_code=403, detail="Only HOD can view statistics")
    
    current_year = 2025  # Focus on 2025
    
    # Get all students in department
    total_students = await db.users.count_documents({
        "role": "student",
        "department": current_user.department,
        "is_approved": True
    })
    
    # Get placed students (Selected status) in 2025
    placed_apps = await db.applications.find({
        "current_round": "Selected"
    }, {"_id": 0}).to_list(1000)
    
    # Filter by department and enrich data
    placed_students_data = []
    for app in placed_apps:
        student = await db.users.find_one({"id": app['student_id']}, {"_id": 0})
        if student and student.get('department') == current_user.department:
            profile = await db.profiles.find_one({"user_id": app['student_id']}, {"_id": 0})
            drive = await db.drives.find_one({"id": app['drive_id']}, {"_id": 0})
            
            placed_students_data.append({
                "student_id": student['id'],
                "name": student['name'],
                "email": student['email'],
                "roll_number": profile.get('roll_number', 'N/A') if profile else 'N/A',
                "cgpa": profile.get('cgpa', 0) if profile else 0,
                "company": drive.get('company_name', 'N/A') if drive else 'N/A',
                "role": drive.get('role', 'N/A') if drive else 'N/A',
                "ai_score": app.get('ai_score', 0),
                "applied_at": app.get('applied_at', ''),
                "skills": profile.get('skills', []) if profile else []
            })
    
    placement_percentage = (len(placed_students_data) / total_students * 100) if total_students > 0 else 0
    
    # Calculate average CGPA of placed students
    avg_cgpa_placed = sum(s['cgpa'] for s in placed_students_data if s['cgpa']) / len(placed_students_data) if placed_students_data else 0
    
    # Company-wise distribution
    company_distribution = {}
    for student in placed_students_data:
        company = student['company']
        if company in company_distribution:
            company_distribution[company] += 1
        else:
            company_distribution[company] = 1
    
    company_stats = [{"company": k, "count": v} for k, v in company_distribution.items()]
    company_stats.sort(key=lambda x: x['count'], reverse=True)
    
    # CGPA distribution
    cgpa_ranges = {
        "9.0-10.0": 0,
        "8.0-8.9": 0,
        "7.0-7.9": 0,
        "6.0-6.9": 0,
        "Below 6.0": 0
    }
    
    for student in placed_students_data:
        cgpa = student['cgpa']
        if cgpa >= 9.0:
            cgpa_ranges["9.0-10.0"] += 1
        elif cgpa >= 8.0:
            cgpa_ranges["8.0-8.9"] += 1
        elif cgpa >= 7.0:
            cgpa_ranges["7.0-7.9"] += 1
        elif cgpa >= 6.0:
            cgpa_ranges["6.0-6.9"] += 1
        else:
            cgpa_ranges["Below 6.0"] += 1
    
    cgpa_distribution = [{"range": k, "count": v} for k, v in cgpa_ranges.items()]
    
    return {
        "year": current_year,
        "department": current_user.department,
        "total_students": total_students,
        "placed_students": len(placed_students_data),
        "placement_percentage": round(placement_percentage, 2),
        "avg_cgpa_placed": round(avg_cgpa_placed, 2),
        "placed_students_details": placed_students_data,
        "company_distribution": company_stats,
        "cgpa_distribution": cgpa_distribution
    }

@api_router.get("/hod/export-report")
async def export_report(current_user: User = Depends(get_current_user)):
    if current_user.role != "hod":
        raise HTTPException(status_code=403, detail="Only HOD can export reports")
    
    # Get placement data
    placed_apps = await db.applications.find({
        "current_round": "Selected"
    }, {"_id": 0}).to_list(1000)
    
    # Filter and enrich data
    report_data = []
    for app in placed_apps:
        student = await db.users.find_one({"id": app['student_id']}, {"_id": 0})
        if student and student.get('department') == current_user.department:
            profile = await db.profiles.find_one({"user_id": app['student_id']}, {"_id": 0})
            drive = await db.drives.find_one({"id": app['drive_id']}, {"_id": 0})
            
            report_data.append({
                "Name": student['name'],
                "Roll Number": profile.get('roll_number', 'N/A'),
                "CGPA": profile.get('cgpa', 'N/A'),
                "Company": drive.get('company_name', 'N/A'),
                "Role": drive.get('role', 'N/A'),
                "Department": student.get('department', 'N/A')
            })
    
    file_path = await generate_excel_report(report_data, current_user.department)
    
    return {"message": "Report generated", "file_path": file_path}

@api_router.get("/hod/export-pdf-performance")
async def export_pdf_performance(current_user: User = Depends(get_current_user)):
    if current_user.role != "hod":
        raise HTTPException(status_code=403, detail="Only HOD can export reports")
    
    # Get 2025 placement data
    placed_apps = await db.applications.find({
        "current_round": "Selected"
    }, {"_id": 0}).to_list(1000)
    
    # Filter and enrich data
    report_data = []
    for app in placed_apps:
        student = await db.users.find_one({"id": app['student_id']}, {"_id": 0})
        if student and student.get('department') == current_user.department:
            profile = await db.profiles.find_one({"user_id": app['student_id']}, {"_id": 0})
            drive = await db.drives.find_one({"id": app['drive_id']}, {"_id": 0})
            
            report_data.append({
                "Name": student['name'],
                "Roll Number": profile.get('roll_number', 'N/A'),
                "CGPA": profile.get('cgpa', 'N/A'),
                "Company": drive.get('company_name', 'N/A'),
                "Role": drive.get('role', 'N/A'),
                "Status": "Selected"
            })
    
    file_path = await generate_student_performance_pdf(report_data, current_user.department, 2025)
    
    return {"message": "PDF report generated", "file_path": file_path}

@api_router.get("/hod/export-pdf-students")
async def export_pdf_students(current_user: User = Depends(get_current_user)):
    if current_user.role != "hod":
        raise HTTPException(status_code=403, detail="Only HOD can export reports")
    
    # Get all students in department
    students = await db.users.find({
        "role": "student",
        "department": current_user.department
    }, {"_id": 0, "password": 0}).to_list(1000)
    
    # Enrich with profile data
    student_data = []
    for student in students:
        profile = await db.profiles.find_one({"user_id": student['id']}, {"_id": 0})
        student_data.append({
            "name": student['name'],
            "email": student['email'],
            "roll_number": profile.get('roll_number', 'N/A') if profile else 'N/A',
            "cgpa": profile.get('cgpa', 'N/A') if profile else 'N/A',
            "skills": profile.get('skills', []) if profile else [],
            "is_approved": student.get('is_approved', False)
        })
    
    file_path = await generate_student_list_pdf(student_data, current_user.department)
    
    return {"message": "PDF report generated", "file_path": file_path}

# ======================== ADMIN/TPO ANALYTICS ========================

@api_router.get("/analytics")
async def get_analytics(current_user: User = Depends(get_current_user)):
    if current_user.role != "tpo":
        raise HTTPException(status_code=403, detail="Only TPO can view analytics")
    
    # Total drives
    total_drives = await db.drives.count_documents({})
    
    # Total applications
    total_applications = await db.applications.count_documents({})
    
    # Placement stats
    selected_count = await db.applications.count_documents({"current_round": "Selected"})
    total_students = await db.users.count_documents({"role": "student", "is_approved": True})
    
    placement_rate = (selected_count / total_students * 100) if total_students > 0 else 0
    
    # Department-wise stats
    departments = ["CSE", "ECE", "EEE", "MECH", "CIVIL"]
    dept_stats = []
    
    for dept in departments:
        dept_students = await db.users.count_documents({
            "role": "student",
            "department": dept,
            "is_approved": True
        })
        
        # Get placed students
        all_placed = await db.applications.find({"current_round": "Selected"}, {"_id": 0}).to_list(1000)
        dept_placed = 0
        for app in all_placed:
            student = await db.users.find_one({"id": app['student_id']}, {"_id": 0})
            if student and student.get('department') == dept:
                dept_placed += 1
        
        dept_stats.append({
            "department": dept,
            "total": dept_students,
            "placed": dept_placed,
            "percentage": round((dept_placed / dept_students * 100) if dept_students > 0 else 0, 2)
        })
    
    return {
        "total_drives": total_drives,
        "total_applications": total_applications,
        "total_students": total_students,
        "placed_students": selected_count,
        "placement_rate": round(placement_rate, 2),
        "department_stats": dept_stats
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
