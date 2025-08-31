import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://tcc-n8n.6v8shu.easypanel.host/webhook/1e6343a0-6e0b-43c2-a301-0d3c0efb64f5")
    REDIS_HOST = os.getenv("REDIS_HOST", "147.93.185.41")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "4f2599e42acfa5ab6740")
    DEFAULT_DB_ID = os.getenv("DEFAULT_DB_ID", "65ff3a7b8f1e4b23d4a9c1d2")
