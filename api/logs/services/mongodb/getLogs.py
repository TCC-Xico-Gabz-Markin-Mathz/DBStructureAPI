from api.logs.services.mongodb.connection import MongoDB


def get_db_logs():
    try:
        mongodb = MongoDB()
        collection = mongodb.collection

        result = list(collection.find())

        logs = [{**log, "_id": str(log["_id"])} for log in result]

        return logs
    except Exception as e:
        raise e
