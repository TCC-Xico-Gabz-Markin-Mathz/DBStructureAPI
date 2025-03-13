import os
import pymongo

class MongoDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        MONGO_URI = f"mongodb://{os.getenv('MONGODB_USER')}:{os.getenv('MONGODB_PASSWORD')}@{os.getenv('MONGODB_HOST')}/{os.getenv('MONGODB_DATABASE')}?authSource=admin"
        self.client = pymongo.MongoClient(MONGO_URI)
        self.database = self.client[os.getenv("MONGODB_DATABASE")]
        self.collection = self.database[os.getenv("MONGODB_COLLECTION")]
