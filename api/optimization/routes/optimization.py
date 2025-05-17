from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.common.services.rag import RAGClient
from api.dependencies import get_mysql_instance, get_rag_client
from api.optimization.helpers.formatResult import (
    format_database_create,
    format_result,
    format_sql_commands,
)
from api.optimization.models.optimize import OptimizeQueryRequest
from api.structure.helpers.mongoToString import convert_db_structure_to_string
from api.structure.services.mongodb.getTables import get_db_structure


router = APIRouter(prefix="/optimize", tags=["optimization"])


@router.post("/")
def optimize_query(
    data: OptimizeQueryRequest,
    rag_client: RAGClient = Depends(get_rag_client),
    mysql_instance=Depends(get_mysql_instance),
):
    database_structure = get_db_structure("65ff3a7b8f1e4b23d4a9c1d2")
    string_structure = convert_db_structure_to_string(database_structure)

    # 1. ask to rag to generate the optimization
    payload_generate = {"database_structure": string_structure, "query": data.query}
    response_generate = rag_client.post("/optimizer/generate", payload_generate)
    formatted_queries = format_result(response_generate)

    # 2. ask to rag to generate the command
    payload_create = {"database_structure": string_structure}
    response_create = rag_client.post("/optimizer/create-database", payload_create)
    create_statements = format_database_create(response_create)

    # 3. create the test instance
    mysql_instance.start_instance()
    mysql_instance.execute_sql_statements(create_statements)

    # 4. ask to rag to populate the db
    payload_populate = {"creation_command": string_structure, "number_insertions": 5}
    response_populate = rag_client.post("/optimizer/populate", payload_populate)
    populate_statements = format_sql_commands(response_populate["sql"])
    # print(populate_statements)
    mysql_instance.execute_sql_statements(populate_statements)

    # 5. execute the original query
    result = mysql_instance.execute_raw_query(data.query)
    print("Resultado da query original:", result)

    # 6. Delete test instance
    mysql_instance.delete_instance()

    return {
        "optimized_queries": formatted_queries,
        "query_result": result,
    }

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
