from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from uuid import UUID

class TheatreBase(BaseModel):
    name: str
    area: str
    city: str


class CreateTheatreSchema(TheatreBase):
    operator_email: EmailStr
    model_config = ConfigDict(str_to_lower=True)


class TheatreOutSchema(TheatreBase):
    id: UUID
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class UpdateTheatreSchema(BaseModel):
    """Used for partially updating a theatre's name/area/city."""

    model_config = ConfigDict(str_to_lower=True)

    name: str | None = None
    area: str | None = None
    city: str | None = None