from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from datetime import timedelta
from uuid import UUID


class MovieBase(BaseModel):
    model_config = ConfigDict(str_to_lower=True, from_attributes=True)

    name: str
    description: str
    rating: float
    genre: str
    imdb_id: str


class CreateMovieRequest(BaseModel):
    imdb_id: str | None = None
    title: str | None = None

    @model_validator(mode="after")
    def validate_input(self):
        if not self.imdb_id and not self.title:
            raise ValueError("Provide either imdb_id or title")

        if self.imdb_id and self.title:
            raise ValueError("Provide only one of imdb_id or title")

        return self


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


class UpdateMovieSchema(BaseModel):
    """Used for partially updating a movie's editable fields.

    `duration` and `imdb_id` are intentionally excluded: duration drives
    show-overlap validation and ticket-expiry math for already-scheduled
    shows, and imdb_id is the movie's identity key.
    """

    model_config = ConfigDict(str_to_lower=True)

    name: str | None = None
    description: str | None = None
    rating: float | None = None
    genre: str | None = None
