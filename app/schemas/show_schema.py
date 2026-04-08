from pydantic import BaseModel, ConfigDict, Field, AliasPath
from datetime import datetime
from typing import Dict, Any
from uuid import UUID


class CreateShowSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)
    start_time: datetime
    screen_id: str
    movie_id: str
    category_price: Dict[str, float]


class ShowOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    start_time: datetime
    screen_id: UUID
    movie_id: UUID
    category_pricing: Dict[str, Any] = Field(alias="category_pricing")
    is_deleted: bool


class ShowDetailOutSchema(ShowOutSchema):
    movie_name: str = Field(validation_alias=AliasPath("movie", "name"))
    theatre_name: str = Field(validation_alias=AliasPath("screen", "theatre", "name"))
    screen_name: str = Field(validation_alias=AliasPath("screen", "name"))
