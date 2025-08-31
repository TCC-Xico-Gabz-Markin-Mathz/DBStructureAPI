import os
import requests
from dotenv import load_dotenv

load_dotenv()


class RAGClient:
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        self.base_url = os.getenv("RAG_BASE_URL")
        if not self.base_url:
            raise ValueError("A variável de ambiente RAG_BASE_URL não está definida.")

        self.headers = {
            "X-API-Key": os.getenv("RAG_API_KEY"),
            "Content-Type": "application/json",
        }

    def post(self, route: str, body: dict, model_name: str = "hermes"):
        url = f"{self.base_url}{route}?model_name={model_name}"
        response = requests.post(
            url, json=body, headers=self.headers
        )

        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()