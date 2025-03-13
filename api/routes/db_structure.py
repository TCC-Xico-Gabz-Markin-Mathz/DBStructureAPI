from fastapi import APIRouter
from api.models.mysqlDBModels import DatabaseModel, UpdateDBTablesQuery
from api.models.tableModels import TableModel
from api.services.mysql.getTables import getTables
from api.services.mongodb.updateTables import update_db_structure as update_db


router = APIRouter(
    prefix="/db_structure",
    tags=["db_structure"]
)

@router.post("/")
def update_db_structure(query: UpdateDBTablesQuery) -> DatabaseModel:
    tables: list[TableModel] = getTables(database=f"{query.name}_{query.id}")

    database = DatabaseModel(_id=query.id, name=query.name, tables=tables)

    update_db(database)

    return database
