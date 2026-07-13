from pydantic import BaseModel, ConfigDict
from uuid import UUID


class CreateLayoutSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)

    name: str
    layout: dict
    theatre_id: UUID


class UpdateLayoutSchema(BaseModel):
    """Used for renaming a layout.

    The seat grid itself is intentionally not editable here: screens and
    shows already reference this layout's seat_mapping/categories, so
    changing the grid after the fact could silently invalidate them.
    """

    model_config = ConfigDict(str_to_lower=True)

    name: str | None = None
