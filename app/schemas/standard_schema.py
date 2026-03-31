
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel


T = TypeVar("T")


class ResponseSchema(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None


def create_response(
    data: Any = None, message: str = "Success", success: bool = True
) -> ResponseSchema:
    return ResponseSchema(data=data, message=message, success=success)