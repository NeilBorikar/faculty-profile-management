import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "faculty_profile_db"
    UPLOAD_DIR: str = "uploads"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure local upload directories exist
for subfolder in ["photos", "resumes", "certificates"]:
    os.makedirs(os.path.join(settings.UPLOAD_DIR, subfolder), exist_ok=True)
