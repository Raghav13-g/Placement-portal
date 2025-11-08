# Placement-portal
Placement Management Portal to streamline campus recruitment processes for colleges. The system should support multiple roles — Student, Head of Department (HOD), and Training &amp; Placement Officer (TPO) — and manage all aspects of placement activities.
Role of my team mates:
Nikhil:Backend, Raghav: Frontend, Nikhil Nirala: Frontend, Hemanth: Backend and Server.
Setup and run instructions:
# TalentBridge - AI-Integrated College Placement Management Portal

A comprehensive full-stack web application for managing college placement activities with AI-powered resume parsing and intelligent candidate matching.

## 🚀 Features

### Student Portal
- *Profile Management*: Create and update academic profiles with CGPA, skills, and roll numbers
- *AI Resume Upload*: Upload PDF/DOCX resumes with automatic skill extraction using Gemini AI
- *Job Applications*: Browse and apply to placement drives
- *Application Tracking*: Real-time status updates across 4 selection rounds
- *AI Match Score*: See intelligent resume-job matching scores

### HOD Portal
- *Student Approval*: Approve student registrations department-wise
- *Analytics Dashboard*: 
  - 5-year historical placement trends
  - Average package trends
  - Company-wise placement distribution
  - Department performance metrics
- *Excel Report Export*: Generate detailed placement reports

### TPO/Admin Portal
- *Drive Management*: Create and manage placement drives with eligibility criteria
- *Round-based Selection*:
  - *Aptitude Round*: Initial screening
  - *Coding Round*: Technical assessment
  - *Group Discussion*: Communication evaluation
  - *HR Round*: Final interview
  - *Selected*: Offer letter stage
- *AI Resume Filtering*: Automatic candidate ranking using AI scoring
- *Email Notifications*: Automated emails to students for each round progression
- *Analytics*: Department-wise placement statistics and overall metrics

## 🛠 Tech Stack

### Frontend
- *React 19* with React Router
- *TailwindCSS* for styling
- *Shadcn UI* components
- *Recharts* for data visualization
- *Axios* for API calls

### Backend
- *FastAPI* (Python)
- *MongoDB* with Motor (async driver)
- *JWT* for authentication
- *Bcrypt* for password hashing
- *Emergent Integrations* for AI (Gemini 2.0)

### AI/ML Features
- *Resume Parsing*: Gemini 2.0 Flash for intelligent text extraction
- *Skill Extraction*: AI-powered skill identification from resumes
- *Resume Scoring*: TF-IDF + Cosine Similarity + CGPA weighting algorithm
- *Job Matching*: Intelligent candidate-job matching

## 🎯 Login Credentials (Sample Data)

### TPO (Training & Placement Officer)
- Email: tpo@college.edu
- Password: tpo123

### HOD (Head of Department)
- CSE: hod.cse@college.edu / hod123
- ECE: hod.ece@college.edu / hod123
- EEE: hod.eee@college.edu / hod123
- MECH: hod.mech@college.edu / hod123
- CIVIL: hod.civil@college.edu / hod123

### Students
- Email: student1@college.edu to student20@college.edu
- Password: student123 (for all students)

## 🔄 Placement Process Flow

1. *Student Registration* → HOD Approval
2. *Profile Creation* → Resume Upload (AI parsing)
3. *Drive Creation* → TPO creates placement opportunities
4. *Application* → Students apply to drives
5. *AI Scoring* → Automatic resume-job matching
6. *Round Selection*:
   - TPO reviews candidates sorted by AI score
   - Selects students for each round (Aptitude, Coding, Group Discussion, HR)
   - System sends automated email notifications
7. *Final Selection* → Offer letter notification via email

## 🤖 AI Features

### Resume Parsing
- Extracts skills, education, and experience from PDF/DOCX files
- Uses Gemini 2.0 Flash with file attachment support
- Fallback to traditional parsing if AI fails

### Resume Scoring Algorithm

Total Score (100) = Text Similarity (60) + Skills Match (30) + CGPA Score (10)

- *Text Similarity*: TF-IDF vectorization + Cosine similarity
- *Skills Match*: Percentage of required skills matched
- *CGPA Score*: Normalized CGPA with threshold validation

## 📊 Sample Data Included

- 1 TPO account
- 5 HOD accounts (one per department)
- 20 student accounts across departments
- 5 active placement drives
- 45 applications with various statuses
- 5 years of historical placement data for analytics

## 🎨 UI Highlights

- Modern gradient backgrounds per role
- Responsive card-based layouts
- Interactive charts with Recharts
- Color-coded status badges
- Toast notifications for feedback
- Clean, professional design

## 📧 Email Integration

Automated email notifications sent from TPO's email for:
- Round selection (all 4 rounds)
- Final selection with offer details
- SMTP encryption with Gmail

## 🔒 Security

- JWT token-based authentication
- Bcrypt password hashing
- Role-based access control
- File upload validation (PDF/DOCX, max 5MB)
- Encrypted email communication

## 📈 Analytics Features

### HOD Dashboard
- 5-year placement trends (bar charts)
- Average package analysis (line charts)
- Top recruiting companies
- Historical data tables
- Excel export functionality

### TPO Dashboard
- Overall placement rate
- Department-wise comparison
- Total drives and applications
- Performance metrics
AI tools used:
GPT, Emergent LLM Key using Gemini, Resume parsing, skill extraction, Resume scoring with TF-
IDF,Cosine Similarity+ CGPA weighting.


