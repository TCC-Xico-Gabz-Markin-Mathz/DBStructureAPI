from pydantic import BaseModel
from api.structure.models.columnModels import ColumnModel


class TableModel(BaseModel):
    table_name: str
    columns: list[ColumnModel]
