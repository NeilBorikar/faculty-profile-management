from bson import ObjectId
from typing import List, Optional, Dict
from app.database import get_profiles_collection
from app.models import serialize_mongo_doc, serialize_mongo_docs
from app.schemas import FacultyProfileCreate, FacultyProfileUpdate

async def get_profile_by_id(profile_id: str) -> Optional[dict]:
    try:
        coll = get_profiles_collection()
        doc = await coll.find_one({"_id": ObjectId(profile_id)})
        return serialize_mongo_doc(doc)
    except Exception:
        return None

async def get_profile_by_email(email: str) -> Optional[dict]:
    coll = get_profiles_collection()
    doc = await coll.find_one({"email": email.lower()})
    return serialize_mongo_doc(doc)

async def get_all_profiles(
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None
) -> List[dict]:
    coll = get_profiles_collection()
    query = {}
    
    if department:
        query["department"] = department
        
    if status:
        query["status"] = status
        
    if search:
        # Case-insensitive text search on name or email
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"designation": {"$regex": search, "$options": "i"}},
        ]
        
    cursor = coll.find(query)
    docs = await cursor.to_list(length=1000)
    return serialize_mongo_docs(docs)

async def create_profile(profile: FacultyProfileCreate) -> dict:
    coll = get_profiles_collection()
    
    # Check if profile already exists
    existing = await get_profile_by_email(profile.email)
    if existing:
        return existing
        
    doc = profile.model_dump()
    doc["email"] = doc["email"].lower()
    doc["status"] = "Pending"
    doc["photo_url"] = None
    doc["resume_url"] = None
    doc["academic_credentials"] = []
    doc["research_publications"] = []
    
    result = await coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_mongo_doc(doc)

async def update_profile(profile_id: str, profile_update: FacultyProfileUpdate) -> Optional[dict]:
    try:
        coll = get_profiles_collection()
        update_data = {k: v for k, v in profile_update.model_dump().items() if v is not None}
        
        if not update_data:
            return await get_profile_by_id(profile_id)
            
        await coll.update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": update_data}
        )
        return await get_profile_by_id(profile_id)
    except Exception:
        return None

async def update_profile_status(profile_id: str, status: str) -> Optional[dict]:
    try:
        coll = get_profiles_collection()
        await coll.update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": {"status": status}}
        )
        return await get_profile_by_id(profile_id)
    except Exception:
        return None

async def update_profile_file_url(profile_id: str, field_name: str, url: str) -> Optional[dict]:
    try:
        coll = get_profiles_collection()
        await coll.update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": {field_name: url}}
        )
        return await get_profile_by_id(profile_id)
    except Exception:
        return None

async def get_analytics() -> Dict:
    coll = get_profiles_collection()
    
    # 1. Total profiles count
    total_count = await coll.count_documents({})
    
    # 2. Status counts
    pending_count = await coll.count_documents({"status": "Pending"})
    approved_count = await coll.count_documents({"status": "Approved"})
    rejected_count = await coll.count_documents({"status": "Rejected"})
    
    # 3. Department breakdown aggregation
    dept_pipeline = [
        {"$group": {"_id": "$department", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    dept_cursor = coll.aggregate(dept_pipeline)
    dept_results = await dept_cursor.to_list(length=100)
    departments = {item["_id"]: item["count"] for item in dept_results if item["_id"]}
    
    # 4. Mock file count and size stats for Data Engineering dashboard
    # This represents tracking metadata in our database about "cloud storage" utilization
    files_uploaded = 0
    cursor = coll.find({})
    async for profile in cursor:
        if profile.get("photo_url"):
            files_uploaded += 1
        if profile.get("resume_url"):
            files_uploaded += 1
        for cred in profile.get("academic_credentials", []):
            if cred.get("certificate_url"):
                files_uploaded += 1
                
    # Approximate storage calculations (mock data engineering stats)
    # Average photo = 1.2MB, PDF resume = 2.4MB, PDF certificate = 1.8MB
    approx_storage_mb = round(files_uploaded * 1.8, 2)
    
    return {
        "total_faculty": total_count,
        "status_counts": {
            "Pending": pending_count,
            "Approved": approved_count,
            "Rejected": rejected_count
        },
        "department_distribution": departments,
        "cloud_storage": {
            "files_count": files_uploaded,
            "used_storage_mb": approx_storage_mb,
            "provider": "LOCAL"
        }
    }
