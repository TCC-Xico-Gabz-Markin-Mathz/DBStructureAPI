import pymongo


class MongoDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.database = self.client["teste"]
        self.collection = self.database["dbstructure"]
