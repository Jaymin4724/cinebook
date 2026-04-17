from pydantic import BaseModel, ConfigDict
from uuid import UUID


class CreateLayoutSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)

    name: str
    layout: dict
    theatre_id: UUID
