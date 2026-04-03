from pydantic import BaseModel, EmailStr, ConfigDict
from enum import Enum

class Roles(str, Enum):
    USER = "user"
    ADMIN = "admin"
    THEATRE_ADMIN = "theatre_admin"

class CreateUserSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)

    email: EmailStr
    otp: str
    role: Roles