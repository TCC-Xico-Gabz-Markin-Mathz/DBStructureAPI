from pydantic import BaseModel, Field

from api.helpers.objectid import PydanticObjectId
from api.models.tableModels import TableModel


class DatabaseModel(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    name: str
    tables: list[TableModel]

class UpdateDBTablesQuery(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    name: str