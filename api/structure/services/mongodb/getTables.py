from api.common.helpers.objectid import PydanticObjectId
from bson import ObjectId

from api.common.services.mongo.connection import MongoDB


def get_db_structure(db_id: PydanticObjectId):
    try:
        mongodb = MongoDB("dbstructure")
        collection = mongodb.collection
        query_filter = {"_id": ObjectId(db_id)}

        result = collection.find_one(query_filter)
        return result
    except Exception as e:
        raise e
