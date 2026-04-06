from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import timedelta
from uuid import UUID

class MovieBase(BaseModel):
    model_config = ConfigDict(str_to_lower=True, from_attributes=True)

    name: str
    description: str
    rating: float
    genre: str
    imdb_id: str


class CreateMovieSchema(MovieBase):
    duration: int

    @field_validator("duration")
    @classmethod
    def transform_to_timedelta(cls, v: int) -> timedelta:
        return timedelta(minutes=v)


class MovieOutSchema(MovieBase):
    id: UUID
    duration: timedelta
    is_deleted: bool
