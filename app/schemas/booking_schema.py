from pydantic import BaseModel, ConfigDict, Field, AliasPath
from datetime import datetime
from uuid import UUID


class BookedSeatOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seats_number: str
    is_cancelled: bool


class BookingOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    show_id: UUID
    total_bill: float
    number_of_seats: int
    is_cancelled: bool
    created_at: datetime
    movie_name: str = Field(validation_alias=AliasPath("show", "movie", "name"))
    theatre_name: str = Field(
        validation_alias=AliasPath("show", "screen", "theatre", "name")
    )
    show_start_time: datetime = Field(validation_alias=AliasPath("show", "start_time"))


class BookingDetailOutSchema(BookingOutSchema):
    seats: list[BookedSeatOutSchema] = Field(
        validation_alias=AliasPath("booked_seat_list")
    )
