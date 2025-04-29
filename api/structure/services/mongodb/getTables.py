from api.common.helpers.objectid import PydanticObjectId
from api.structure.services.mongodb.connection import MongoDB
from bson import ObjectId


def get_db_structure(db_id: PydanticObjectId):
    try:
        mongodb = MongoDB()
        collection = mongodb.collection
        query_filter = {"_id": ObjectId(db_id)}

        result = collection.find_one(query_filter)
        return result
    except Exception as e:
        raise e
