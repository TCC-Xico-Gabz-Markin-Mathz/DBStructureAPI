from pydantic import BaseModel


class OptimizeQueryRequest(BaseModel):
    query: str
