import pymongo


class MongoDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        uri = "mongodb://mongo:65c5294460aa71e75831@147.93.185.41:27017/teste?authSource=admin&tls=false"
        self.client = pymongo.MongoClient(uri)
        self.database = self.client["teste"]
        self.collection = self.database["dbstructure"]
