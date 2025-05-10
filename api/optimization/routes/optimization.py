from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.common.services.rag import RAGClient
from api.dependencies import get_mysql_instance, get_rag_client
from api.optimization.helpers.formatResult import format_database_create, format_result
from api.optimization.models.optimize import OptimizeQueryRequest
from api.optimization.service.mySqlInstance import MySQLTestInstance
from api.optimization.service.testingDb import create_db, delete_db, test_queries
from api.structure.helpers.mongoToString import convert_db_structure_to_string
from api.structure.services.mongodb.getTables import get_db_structure


router = APIRouter(prefix="/optimize", tags=["optimization"])


@router.post("/")
def optimize_query(
    data: OptimizeQueryRequest, rag_client: RAGClient = Depends(get_rag_client)
):
    database_structure = get_db_structure("65ff3a7b8f1e4b23d4a9c1d2")
    string_structure = convert_db_structure_to_string(database_structure)

    # ask to rag to generate the optimization
    payload_generate = {"database_structure": string_structure, "query": data.query}
    response_generate = rag_client.post("/optimizer/generate", payload_generate)

    formatted_queries = format_result(response_generate)
    # for i, q in enumerate(formatted_queries, 1):
    #     print(q)

    # ask to rag to generate the command
    payload_create = {"database_structure": string_structure}
    response_create = rag_client.post("/optimizer/create-database", payload_create)
    create_statements = format_database_create(response_create, debug=True)
    print(create_statements)

    # ask to rag to generate the command to create the db
    # payload_optimization_result = {0
    #     "original_metrics": {
    #         "execution_time_ms": 1450,
    #         "rows_scanned": 500000,
    #         "indexes_used": False,
    #     },
    #     "optimized_metrics": {
    #         "execution_time_ms": 210,
    #         "rows_scanned": 12000,
    #         "indexes_used": True,
    #     },
    #     "original_query": "SELECT nome, email FROM clientes WHERE cidade = 'São Paulo';",
    #     "optimized_query": "SELECT nome, email FROM clientes WHERE cidade = 'São Paulo' /*+ INDEX(cidade_idx) */;",
    #     "applied_indexes": ["CREATE INDEX cidade_idx ON clientes(cidade);"],
    # }
    # response = rag_client.post("/rag/optimize/analyze", payload_optimization_result)

    return None

    # create the db instance
    create_db()

    # test the dbs
    test_queries()

    # delete the db instance
    delete_db()

    return None


class TestCommands(BaseModel):
    test_a_command: str
    test_b_command: str


# Endpoint para criar a instância e rodar os testes
@router.post("/create_and_test")
async def create_and_test(mysql_instance=Depends(get_mysql_instance)):
    # Executar o teste (só criar e testar a conexão)
    test_results = mysql_instance.start_instance()

    # Retornar resultados
    return {
        "message": "Teste de criação e conexão concluído",
        "test_results": test_results,
    }


# Endpoint para deletar a instância
@router.delete("/delete_instance")
async def delete_instance(mysql_instance=Depends(get_mysql_instance)):
    mysql_instance.delete_instance()
    return {"message": "Instância MySQL removida com sucesso"}
