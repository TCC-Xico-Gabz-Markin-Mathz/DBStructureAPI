from api.structure.helpers.objectid import PydanticObjectId
from api.structure.services.mongodb.connection import MongoDB


def get_db_structure(db_id: PydanticObjectId):
    try:
        mongodb = MongoDB()
        collection = mongodb.collection
        query_filter = {"_id": db_id}

        result = collection.find_one(query_filter)
        return result
    except Exception as e:
        raise e
