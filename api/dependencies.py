import os
from fastapi import Security
from dotenv import load_dotenv
from fastapi.security import APIKeyHeader
from starlette.exceptions import HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from api.common.services.rag import RAGClient
from api.optimization.service.mySqlInstance import MySQLTestInstance

load_dotenv()

api_key_header = APIKeyHeader(name="X_API_KEY", auto_error=False)


def get_api_key(X_API_Key: str = Security(api_key_header)):
    if X_API_Key == os.getenv("API_KEY"):
        return X_API_Key
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate API KEY"
        )


rag_client_instance = RAGClient()


def get_rag_client():
    return rag_client_instance


mysql_instance_singleton = MySQLTestInstance()


def get_mysql_instance():
    return mysql_instance_singleton
