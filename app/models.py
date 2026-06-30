from bson import ObjectId

def serialize_mongo_doc(doc: dict) -> dict:
    """Converts MongoDB ObjectId to a string representation for JSON compatibility."""
    if not doc:
        return doc
    # Convert ObjectId of the main document
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc

def serialize_mongo_docs(docs: list) -> list:
    """Serializes a list of MongoDB documents."""
    return [serialize_mongo_doc(doc) for doc in docs if doc]

# Helper to check for valid ObjectId
def is_valid_object_id(id_str: str) -> bool:
    try:
        ObjectId(id_str)
        return True
    except Exception:
        return False
