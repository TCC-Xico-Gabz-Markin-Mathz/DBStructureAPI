from api.models.mysqlDBModels import DatabaseModel
from api.services.mongodb.connection import MongoDB


def update_db_structure(database: DatabaseModel):
    try:
        mongodb = MongoDB()
        collection = mongodb.collection
        query_filter = {'name': database.name, '_id': database.id}
        new_values = {'$set': {'tables': database.model_dump()["tables"]}}

        collection.update_one(query_filter, new_values, upsert=True)
        return None
    except Exception as e:
        raise e
