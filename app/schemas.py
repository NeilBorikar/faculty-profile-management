from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

class AcademicCredential(BaseModel):
    degree: str
    institution: str
    passing_year: int
    certificate_url: Optional[str] = None

class ResearchPublication(BaseModel):
    title: str
    journal: str
    publication_year: int
    url: Optional[str] = None

class FacultyProfileCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str
    department: str
    designation: str
    joining_date: str
    bio: Optional[str] = ""

class FacultyProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    joining_date: Optional[str] = None
    bio: Optional[str] = None
    academic_credentials: Optional[List[AcademicCredential]] = None
    research_publications: Optional[List[ResearchPublication]] = None

class FacultyProfileResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: str
    department: str
    designation: str
    joining_date: str
    bio: Optional[str] = ""
    status: str = "Pending" # Pending, Approved, Rejected
    photo_url: Optional[str] = None
    resume_url: Optional[str] = None
    academic_credentials: List[AcademicCredential] = []
    research_publications: List[ResearchPublication] = []

class StatusUpdate(BaseModel):
    status: str = Field(..., description="Must be 'Approved' or 'Rejected'")

class AuthRequest(BaseModel):
    email: str
    role: str = Field(..., description="Must be 'Faculty' or 'Admin'")

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Full name of the faculty member")
    email: EmailStr
    phone: str
    department: str
    designation: str
    joining_date: str = Field(..., description="Date in YYYY-MM-DD format")
    bio: Optional[str] = ""

class RegisterResponse(BaseModel):
    message: str
    profile_id: str
    name: str
    email: str
    status: str

class AuthResponse(BaseModel):
    email: str
    role: str
    name: str
    profile_id: Optional[str] = None
