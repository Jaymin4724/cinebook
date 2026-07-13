from pydantic import BaseModel, ConfigDict
from uuid import UUID


class CreateScreenSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_to_lower=True)

    name: str
    theatre_id: UUID
    layout_id: UUID


class ScreenOutSchema(CreateScreenSchema):
    id: UUID


class UpdateScreenSchema(BaseModel):
    """Used for renaming a screen.

    `layout_id` is intentionally not editable here: shows already
    reference this screen's layout for seat/category pricing.
    """

    model_config = ConfigDict(str_to_lower=True)

    name: str | None = None


class ScreenWithDetailsSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str

    theatre_id: UUID
    theatre_name: str

    layout_id: UUID
    layout_name: str
