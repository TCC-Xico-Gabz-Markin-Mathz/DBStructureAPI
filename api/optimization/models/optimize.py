from enum import Enum
from pydantic import BaseModel


class OptimizeQueryRequest(BaseModel):
    query: str


class ModelName(str, Enum):
    GROQ = "groq"
    GEMMA = "gemma"
    HERMES = "hermes"
    MISTRAL = "mistral"
