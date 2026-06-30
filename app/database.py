import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logger = logging.getLogger("uvicorn")

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_connection = Database()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    try:
        db_connection.client = AsyncIOMotorClient(settings.MONGO_URI)
        db_connection.db = db_connection.client[settings.MONGO_DB_NAME]
        # Quick ping to verify connection
        await db_connection.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB!")
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_connection.client:
        db_connection.client.close()
        logger.info("MongoDB connection closed.")

def get_database():
    return db_connection.db

def get_profiles_collection():
    return db_connection.db["profiles"]
