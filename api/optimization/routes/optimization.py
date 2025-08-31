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

@router.post(
    "/",
    summary="Otimiza uma query SQL",
    description="Recebe uma query SQL e um ID de banco de dados, e retorna uma versão otimizada da query com análises de performance.",
    responses={
        200: {
            "description": "Query otimizada com sucesso.",
            "content": {
                "application/json": {
                    "example": {
                        "analyze": {"analysis": "A query otimizada é mais performática..."},
                        "optimized_queries": ["CREATE INDEX ...", "SELECT ..."],
                        "query_result": [{"id": 1, "name": "John Doe"}],
                    }
                }
            },
        },
        500: {
            "description": "Erro interno no servidor.",
            "content": {
                "application/json": {
                    "example": {"error": "Ocorreu um erro inesperado."}
                }
            },
        },
    },
)
def optimize_query(
    data: OptimizeQueryRequest,
    db_id: str = Query(..., description="ID do banco de dados a ser usado."),
    model_name: str = Query(
        MODEL_NAME, description="Nome do modelo de linguagem a ser usado para a otimização."
    ),
    use_cache: bool = Query(True, description="Define se o cache de Redis deve ser utilizado."),
    mysql_instance=Depends(get_mysql_instance),
    optimization_service: OptimizationService = Depends(get_optimization_service),
):
    return optimization_service.optimize_query_flow(
        db_id, data.query, mysql_instance, model_name, use_cache
    )