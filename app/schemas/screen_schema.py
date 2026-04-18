from pydantic import BaseModel, ConfigDict
from uuid import UUID


class CreateScreenSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_to_lower=True)

    name: str
    theatre_id: UUID
    layout_id: UUID


class ScreenOutSchema(CreateScreenSchema):
    id: UUID


class ScreenWithDetailsSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str

    theatre_id: UUID
    theatre_name: str

    layout_id: UUID
    layout_name: str
