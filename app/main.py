import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import uvicorn

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, get_profiles_collection
from app.schemas import (
    FacultyProfileCreate,
    FacultyProfileUpdate,
    FacultyProfileResponse,
    StatusUpdate,
    AuthRequest,
    AuthResponse,
    RegisterRequest,
    RegisterResponse
)
import app.crud as crud
from app.storage import get_storage_provider

app = FastAPI(
    title="Cloud-Based Faculty Profile Management API",
    description="REST API for Faculty Profile Management, integrated with MongoDB and Cloudflare R2",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup and shutdown lifecycle events
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    # Auto-seed mock data if database is empty
    coll = get_profiles_collection()
    count = await coll.count_documents({})
    if count == 0:
        await seed_mock_data()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Serve uploaded files locally
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Auth / Login Endpoint
@app.post("/api/auth/login", response_model=AuthResponse)
async def login(auth: AuthRequest):
    email = auth.email.strip().lower()
    
    if auth.role == "Admin":
        return AuthResponse(
            email=email,
            role="Admin",
            name="College Administrator"
        )
    elif auth.role == "Faculty":
        # Search for faculty profile by email
        profile = await crud.get_profile_by_email(email)
        
        # If doesn't exist, create a draft profile
        if not profile:
            # Generate a new draft profile
            new_profile = FacultyProfileCreate(
                name=email.split("@")[0].title().replace(".", " "),
                email=email,
                phone="Not provided",
                department="Computer Science",
                designation="Assistant Professor",
                joining_date="2026-06-30"
            )
            profile = await crud.create_profile(new_profile)
            
        return AuthResponse(
            email=email,
            role="Faculty",
            name=profile["name"],
            profile_id=profile["id"]
        )
    
    raise HTTPException(status_code=400, detail="Invalid role specified")

# Register Endpoint — use via Postman to add a faculty member
@app.post("/api/auth/register", response_model=RegisterResponse, status_code=201)
async def register_faculty(data: RegisterRequest):
    """
    Register a new faculty member.
    Use this endpoint via Postman to pre-register faculty before they log in.
    """
    email = data.email.strip().lower()

    # Check if a profile with this email already exists
    existing = await crud.get_profile_by_email(email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A faculty profile with email '{email}' already exists."
        )

    # Create the new profile in MongoDB
    new_profile = FacultyProfileCreate(
        name=data.name,
        email=email,
        phone=data.phone,
        department=data.department,
        designation=data.designation,
        joining_date=data.joining_date,
        bio=data.bio
    )
    created = await crud.create_profile(new_profile)

    return RegisterResponse(
        message=f"Faculty '{data.name}' registered successfully. Status is Pending until Admin approval.",
        profile_id=created["id"],
        name=created["name"],
        email=created["email"],
        status=created["status"]
    )

# Profile Endpoints
@app.post("/api/profiles", response_model=FacultyProfileResponse)
async def create_new_profile(profile: FacultyProfileCreate):
    existing = await crud.get_profile_by_email(profile.email)
    if existing:
        raise HTTPException(status_code=400, detail="Faculty profile with this email already exists")
    created = await crud.create_profile(profile)
    return created

@app.get("/api/profiles", response_model=List[FacultyProfileResponse])
async def list_profiles(
    search: Optional[str] = Query(None, description="Search by name, email, or designation"),
    department: Optional[str] = Query(None, description="Filter by department"),
    status: Optional[str] = Query(None, description="Filter by status (Pending, Approved, Rejected)")
):
    return await crud.get_all_profiles(search, department, status)

@app.get("/api/profiles/{profile_id}", response_model=FacultyProfileResponse)
async def get_profile(profile_id: str):
    profile = await crud.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    return profile

@app.put("/api/profiles/{profile_id}", response_model=FacultyProfileResponse)
async def update_profile(profile_id: str, profile_update: FacultyProfileUpdate):
    profile = await crud.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    updated = await crud.update_profile(profile_id, profile_update)
    return updated

# File Upload Endpoint (Abstraced Local vs Cloudflare R2)
@app.post("/api/profiles/{profile_id}/upload")
async def upload_profile_file(
    profile_id: str,
    category: str = Form(..., description="Must be 'photos', 'resumes', or 'certificates'"),
    file: UploadFile = File(...)
):
    profile = await crud.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
        
    if category not in ["photos", "resumes", "certificates"]:
        raise HTTPException(status_code=400, detail="Invalid category. Use 'photos', 'resumes', or 'certificates'.")
        
    try:
        # Get storage provider and upload file
        provider = get_storage_provider()
        file_url = await provider.upload_file(file, category)
        
        # Save reference URL to the database
        field_name = "photo_url" if category == "photos" else "resume_url"
        
        if field_name in ["photo_url", "resume_url"]:
            await crud.update_profile_file_url(profile_id, field_name, file_url)
            
        return {
            "message": f"File uploaded successfully to {category}!",
            "url": file_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Admin Status Verification Endpoint
@app.patch("/api/profiles/{profile_id}/status", response_model=FacultyProfileResponse)
async def verify_profile(profile_id: str, update: StatusUpdate):
    if update.status not in ["Approved", "Rejected"]:
        raise HTTPException(status_code=400, detail="Status must be 'Approved' or 'Rejected'")
        
    profile = await crud.get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
        
    updated = await crud.update_profile_status(profile_id, update.status)
    return updated

# Analytics Dashboard Endpoint
@app.get("/api/analytics")
async def get_dashboard_analytics():
    return await crud.get_analytics()

# Manual Seed Trigger
@app.post("/api/seed")
async def trigger_seed():
    await seed_mock_data()
    return {"message": "Database seeded with sample faculty profiles."}

# Mock Database Seeder Function
async def seed_mock_data():
    coll = get_profiles_collection()
    # Clear existing mock data first
    await coll.delete_many({})
    
    mock_faculty = [
        {
            "name": "Dr. Sarah Jenkins",
            "email": "sarah.jenkins@college.edu",
            "phone": "+1 (555) 123-4567",
            "department": "Computer Science",
            "designation": "Professor",
            "joining_date": "2020-08-15",
            "bio": "Specializes in Cloud Data Engineering and Distributed Systems. 10+ years of teaching experience.",
            "status": "Approved",
            "photo_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150",
            "resume_url": None,
            "academic_credentials": [
                {
                    "degree": "Ph.D. in Computer Science",
                    "institution": "Stanford University",
                    "passing_year": 2018,
                    "certificate_url": None
                },
                {
                    "degree": "M.Tech in Software Systems",
                    "institution": "IIT Bombay",
                    "passing_year": 2013,
                    "certificate_url": None
                }
            ],
            "research_publications": [
                {
                    "title": "Optimizing Apache Spark Pipelines in Cloud Deployments",
                    "journal": "International Journal of Cloud Computing",
                    "publication_year": 2024,
                    "url": "https://example.com/pub1"
                }
            ]
        },
        {
            "name": "Prof. Michael Chen",
            "email": "michael.chen@college.edu",
            "phone": "+1 (555) 234-5678",
            "department": "Computer Science",
            "designation": "Associate Professor",
            "joining_date": "2022-01-10",
            "bio": "Enjoys research in Database Internals, MongoDB indexing, and Big Data Query Engines.",
            "status": "Pending",
            "photo_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150",
            "resume_url": None,
            "academic_credentials": [
                {
                    "degree": "M.S. in Computer Science",
                    "institution": "University of California, Berkeley",
                    "passing_year": 2015,
                    "certificate_url": None
                }
            ],
            "research_publications": [
                {
                    "title": "Document Data Store Query Optimization",
                    "journal": "ACM Transactions on Database Systems",
                    "publication_year": 2023,
                    "url": "https://example.com/pub2"
                }
            ]
        },
        {
            "name": "Dr. Elena Rostova",
            "email": "elena.rostova@college.edu",
            "phone": "+1 (555) 345-6789",
            "department": "Electrical Engineering",
            "designation": "Professor",
            "joining_date": "2018-07-22",
            "bio": "Focuses on Cloud-Edge Computing architectures, IoT Sensor Networks, and Embedded Hardware.",
            "status": "Approved",
            "photo_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150",
            "resume_url": None,
            "academic_credentials": [
                {
                    "degree": "Ph.D. in Electrical Engineering",
                    "institution": "MIT",
                    "passing_year": 2016,
                    "certificate_url": None
                }
            ],
            "research_publications": []
        },
        {
            "name": "Prof. David Miller",
            "email": "david.miller@college.edu",
            "phone": "+1 (555) 456-7890",
            "department": "Mechanical Engineering",
            "designation": "Assistant Professor",
            "joining_date": "2024-06-01",
            "bio": "Researching Cloud-based CAD Modeling pipelines and structural simulations using cloud HPC nodes.",
            "status": "Rejected",
            "photo_url": None,
            "resume_url": None,
            "academic_credentials": [],
            "research_publications": []
        }
    ]
    
    await coll.insert_many(mock_faculty)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
