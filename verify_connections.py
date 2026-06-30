import os
import sys
import asyncio
from dotenv import load_dotenv

# Ensure we import from the same path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environmental variables
load_dotenv()

async def test_mongodb_connection():
    print("Checking MongoDB Connection...")
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB_NAME", "faculty_profile_db")
        
        print(f"  - Connecting to URI: {mongo_uri}")
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=3000)
        
        # Ping the admin database to verify connection
        await client.admin.command('ping')
        print(f"  - Success! MongoDB is online.")
        print(f"  - Using database: '{db_name}'")
        
        # Inspect collections
        db = client[db_name]
        collections = await db.list_collection_names()
        print(f"  - Existing collections: {collections}")
        client.close()
        return True
    except Exception as e:
        print(f"  - FAILED! Error connecting to MongoDB: {e}")
        print("  - Please verify your MONGO_URI in the .env file and ensure MongoDB is running.")
        return False

def test_storage_connection():
    print(f"\nChecking Local Storage Configuration...")
    upload_dir = os.getenv("UPLOAD_DIR", "uploads")
    print(f"  - Checking local directory '{upload_dir}'...")
    try:
        os.makedirs(upload_dir, exist_ok=True)
        for sub in ["photos", "resumes", "certificates"]:
            os.makedirs(os.path.join(upload_dir, sub), exist_ok=True)
        
        # Try writing a temp file to ensure it's writable
        temp_file = os.path.join(upload_dir, ".write_test")
        with open(temp_file, "w") as f:
            f.write("test")
        os.remove(temp_file)
        print("  - Success! Local upload folders exist and are writable.")
        return True
    except Exception as e:
        print(f"  - FAILED! Local storage check failed: {e}")
        return False

async def main():
    print("=" * 60)
    print("Cloud Faculty Profile Management System - Configuration Doctor")
    print("=" * 60)
    
    db_ok = await test_mongodb_connection()
    storage_ok = test_storage_connection()
    
    print("\n" + "=" * 60)
    if db_ok and storage_ok:
        print("DIAGNOSIS: ALL SYSTEMS OK! Your cloud stack is properly configured.")
        print("You can now safely run the backend using: python -m app.main")
    else:
        print("DIAGNOSIS: WARNING! One or more services failed configuration tests.")
        print("Please check your .env parameters and ensure dependency processes are running.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
