from fastapi import APIRouter, Depends
from api.common.services.rag import RAGClient
from api.dependencies import get_rag_client
from api.structure.helpers.formatSqlQuery import format_sql_query
from api.structure.helpers.mongoToString import convert_db_structure_to_string
from api.structure.models.mysqlDBModels import (
    DatabaseModel,
    InterfaceQueryRequest,
    UpdateDBTablesQuery,
)
from api.structure.models.tableModels import TableModel
from api.structure.services.mongodb.getTables import get_db_structure
from api.structure.services.mysql.executeQuery import execute_sql_query
from api.structure.services.mysql.getTables import getTables
from api.structure.services.mongodb.updateTables import update_db_structure as update_db


router = APIRouter(prefix="/db_structure", tags=["db_structure"])


@router.post("/")
def update_db_structure(query: UpdateDBTablesQuery) -> DatabaseModel:
    tables: list[TableModel] = getTables(database=f"{query.db_name}")

    database = DatabaseModel(_id=query.db_id, name=query.db_name, tables=tables)

    update_db(database)

    return database


@router.post("/{db_id}")
def interface_request(
    data: InterfaceQueryRequest, rag_client: RAGClient = Depends(get_rag_client)
):
    database_structure = get_db_structure(data.db_id)
    string_structure = convert_db_structure_to_string(database_structure)

    payload = {"database_structure": string_structure, "order": data.order}
    response = rag_client.post("/rag/query/structure", payload)

    database_response = execute_sql_query(
        database=data.db_name, query=format_sql_query(response["query"])
    )

    payload = {"order": data.order, "result": str(database_response)}
    response = rag_client.post("/rag/query/interpreter", payload)

    return response
