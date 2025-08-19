import os
import pymongo


class MongoDB:
    _instances = {}
    _client = None
    _database = None

    def __new__(cls, collection_name):
        if collection_name not in cls._instances:
            cls._instances[collection_name] = super().__new__(cls)
            cls._instances[collection_name]._initialize(collection_name)
        return cls._instances[collection_name]

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            uri = os.getenv(
                "MONGODB_URI",
                "mongodb://root:example@localhost:27017/teste?authSource=admin&tls=false",
            )
            cls._client = pymongo.MongoClient(uri)
            cls._database = cls._client["teste"]
        return cls._database

    def _initialize(self, collection_name):
        database = self._get_client()
        self.collection = database[collection_name]
