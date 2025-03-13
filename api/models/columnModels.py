from pydantic import BaseModel, Field


class ColumnModel(BaseModel):
    name: str
    is_nullable: bool
    type: str
    default: None | str = Field(default=None)
    extra: None | str = Field(default=None)
    is_primary_key: bool
    is_foreign_key: bool
    referenced_table: None | str  = Field(default=None)
    referenced_column: None | str  = Field(default=None)