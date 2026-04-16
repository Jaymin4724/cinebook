from pydantic import BaseModel, ConfigDict
from uuid import UUID


class CreateScreenSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_to_lower=True)

    name: str
    theatre_id: str
    layout_id: str


class ScreenOutSchema(CreateScreenSchema):
    id: UUID
