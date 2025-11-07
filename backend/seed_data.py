import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import random

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_database():
    # Connect to MongoDB
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("Seeding database with sample data...")
    
    # Clear existing data
    await db.users.delete_many({})
    await db.profiles.delete_many({})
    await db.drives.delete_many({})
    await db.applications.delete_many({})
    await db.placement_history.delete_many({})
    
    # Create TPO
    tpo_password = pwd_context.hash("tpo123")
    tpo = {
        "id": "tpo_001",
        "email": "tpo@college.edu",
        "name": "Dr. Rajesh Kumar",
        "role": "tpo",
        "is_approved": True,
        "password": tpo_password,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(tpo)
    print("Created TPO account: tpo@college.edu / tpo123")
    
    # Create HODs for each department
    departments = ["CSE", "ECE", "EEE", "MECH", "CIVIL"]
    hod_names = ["Dr. Priya Sharma", "Dr. Amit Patel", "Dr. Sunita Reddy", "Dr. Vikram Singh", "Dr. Anjali Desai"]
    
    for i, (dept, name) in enumerate(zip(departments, hod_names)):
        hod_password = pwd_context.hash("hod123")
        hod = {
            "id": f"hod_{dept.lower()}",
            "email": f"hod.{dept.lower()}@college.edu",
            "name": name,
            "role": "hod",
            "department": dept,
            "is_approved": True,
            "password": hod_password,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(hod)
        print(f"Created HOD account: hod.{dept.lower()}@college.edu / hod123")
    
    # Create sample students
    student_names = [
        "Arjun Mehta", "Priya Gupta", "Rahul Verma", "Sneha Iyer", "Karan Shah",
        "Ananya Nair", "Rohan Joshi", "Diya Kapoor", "Aditya Rao", "Meera Pillai",
        "Varun Kumar", "Ishita Singh", "Siddharth Menon", "Kavya Reddy", "Nikhil Agarwal",
        "Riya Sharma", "Harsh Patel", "Tanvi Jain", "Akash Malhotra", "Neha Khanna"
    ]
    
    skills_pool = [
        ["Python", "Machine Learning", "Django", "SQL"],
        ["Java", "Spring Boot", "Microservices", "AWS"],
        ["React", "Node.js", "MongoDB", "JavaScript"],
        ["C++", "Data Structures", "Algorithms", "Git"],
        ["Python", "Data Science", "Pandas", "NumPy"],
        ["Angular", "TypeScript", "REST APIs", "Docker"],
        ["Flutter", "Dart", "Mobile Development", "Firebase"],
        ["DevOps", "Kubernetes", "CI/CD", "Jenkins"],
        ["UI/UX", "Figma", "HTML", "CSS"],
        ["Cybersecurity", "Ethical Hacking", "Network Security"],
    ]
    
    for i, name in enumerate(student_names):
        dept = departments[i % len(departments)]
        student_password = pwd_context.hash("student123")
        student = {
            "id": f"student_{i+1:03d}",
            "email": f"student{i+1}@college.edu",
            "name": name,
            "role": "student",
            "department": dept,
            "is_approved": True,
            "password": student_password,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(student)
        
        # Create profile
        profile = {
            "id": f"profile_{i+1:03d}",
            "user_id": student["id"],
            "roll_number": f"2021{dept}{i+1:03d}",
            "cgpa": round(random.uniform(6.5, 9.5), 2),
            "skills": skills_pool[i % len(skills_pool)],
            "resume_url": f"resume_{i+1}.pdf",
            "resume_text": f"Experienced student with strong skills in {', '.join(skills_pool[i % len(skills_pool)][:3])}",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.profiles.insert_one(profile)
    
    print(f"Created {len(student_names)} student accounts (student123 password for all)")
    
    # Create sample placement drives
    companies = [
        {"name": "TechCorp Solutions", "role": "Software Engineer", "min_cgpa": 7.0, "skills": ["Python", "Java", "React"]},
        {"name": "InnovateSys", "role": "Full Stack Developer", "min_cgpa": 7.5, "skills": ["Node.js", "React", "MongoDB"]},
        {"name": "CloudTech Industries", "role": "Cloud Engineer", "min_cgpa": 7.2, "skills": ["AWS", "Docker", "Kubernetes"]},
        {"name": "DataMinds Analytics", "role": "Data Analyst", "min_cgpa": 7.0, "skills": ["Python", "SQL", "Machine Learning"]},
        {"name": "SecureNet Systems", "role": "Cybersecurity Analyst", "min_cgpa": 7.5, "skills": ["Network Security", "Ethical Hacking"]}
    ]
    
    for i, company in enumerate(companies):
        drive = {
            "id": f"drive_{i+1:03d}",
            "company_name": company["name"],
            "role": company["role"],
            "description": f"Join {company['name']} as a {company['role']}. Work on cutting-edge technologies and grow your career.",
            "min_cgpa": company["min_cgpa"],
            "required_skills": company["skills"],
            "eligible_departments": ["CSE", "ECE", "EEE"],
            "deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "created_by": "tpo_001",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.drives.insert_one(drive)
    
    print(f"Created {len(companies)} placement drives")
    
    # Create 5-year historical placement data
    historical_companies = [
        "TechCorp", "InnovateSys", "CloudTech", "DataMinds", "SecureNet",
        "Infosys", "TCS", "Wipro", "Cognizant", "Accenture"
    ]
    
    historical_roles = [
        "Software Engineer", "Systems Engineer", "Analyst", "Developer",
        "Associate Engineer", "Junior Developer"
    ]
    
    current_year = datetime.now().year
    
    for year in range(current_year - 5, current_year):
        for dept in departments:
            # Create 5-8 records per department per year
            num_records = random.randint(5, 8)
            for _ in range(num_records):
                history = {
                    "id": f"history_{year}_{dept}_{_}",
                    "year": year,
                    "department": dept,
                    "company_name": random.choice(historical_companies),
                    "role": random.choice(historical_roles),
                    "students_placed": random.randint(2, 15),
                    "avg_package": round(random.uniform(3.5, 12.0), 1)
                }
                await db.placement_history.insert_one(history)
    
    print(f"Created 5-year historical placement data")
    
    # Create some sample applications
    students = await db.users.find({"role": "student"}).to_list(100)
    drives = await db.drives.find({}).to_list(100)
    
    for i, student in enumerate(students[:15]):  # First 15 students apply
        for j, drive in enumerate(drives[:3]):  # To first 3 drives
            profile = await db.profiles.find_one({"user_id": student["id"]})
            
            # Calculate a simple AI score
            ai_score = round(random.uniform(60, 95), 2)
            
            # Assign different rounds to show progression
            rounds = ["Applied", "Aptitude", "Coding", "Group Discussion", "HR", "Selected"]
            current_round = rounds[min(i % 6, len(rounds) - 1)]
            
            round_history = []
            if current_round != "Applied":
                round_idx = rounds.index(current_round)
                for r in rounds[1:round_idx + 1]:
                    round_history.append({
                        "round": r,
                        "selected_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 20))).isoformat()
                    })
            
            application = {
                "id": f"app_{i}_{j}",
                "drive_id": drive["id"],
                "student_id": student["id"],
                "status": "Active",
                "ai_score": ai_score,
                "current_round": current_round,
                "round_history": round_history,
                "applied_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))).isoformat()
            }
            await db.applications.insert_one(application)
    
    print(f"Created sample applications")
    
    print("\n=== Database seeded successfully! ===")
    print("\nLogin Credentials:")
    print("TPO: tpo@college.edu / tpo123")
    print("HODs: hod.cse@college.edu / hod123 (and similar for other departments)")
    print("Students: student1@college.edu / student123 (student1 to student20)")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
