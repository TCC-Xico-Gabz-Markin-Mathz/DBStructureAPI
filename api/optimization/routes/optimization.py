from fastapi import APIRouter, Depends, Query
from api.common.services.rag import RAGClient
from api.dependencies import get_mysql_instance, get_rag_client
from api.optimization.models.optimize import ModelName, OptimizeQueryRequest
from api.common.services.cache import CacheService
from api.optimization.service.optimization_service import OptimizationService
from api.config import Config

# Config
router = APIRouter(prefix="/optimize", tags=["optimization"])
MODEL_NAME = ModelName.GROQ.value

# Initialize services
cache_service = CacheService(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=Config.REDIS_DB,
    password=Config.REDIS_PASSWORD,
)


def get_optimization_service(rag_client: RAGClient = Depends(get_rag_client)):
    return OptimizationService(
        rag_client, cache_service, Config.WEBHOOK_URL, Config.DEFAULT_DB_ID
    )


@router.post("/")
def optimize_query(
    data: OptimizeQueryRequest,
    db_id: str = Query(..., description="Database ID"),
    model_name: str = Query(
        MODEL_NAME, description="Model name to use for optimization"
    ),
    mysql_instance=Depends(get_mysql_instance),
    optimization_service: OptimizationService = Depends(get_optimization_service),
):
    return optimization_service.optimize_query_flow(
        db_id, data.query, mysql_instance, model_name
    )
