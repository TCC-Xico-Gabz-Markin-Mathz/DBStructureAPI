from pydantic import BaseModel
from api.models.columnModels import ColumnModel


class TableModel(BaseModel):
    table_name: str
    columns: list[ColumnModel]
