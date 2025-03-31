from api.common.helpers.objectid import PydanticObjectId
from api.structure.services.mongodb.connection import MongoDB


def get_db_structure(db_id: PydanticObjectId):
    try:
        mongodb = MongoDB()
        collection = mongodb.collection

        result = collection.find()
        return result
    except Exception as e:
        raise e
