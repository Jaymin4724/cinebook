from pydantic import BaseModel, EmailStr
from enum import Enum

class Roles(str, Enum):
    USER = "user"
    ADMIN = "admin"
    THEATRE_ADMIN = "theatre_admin"

class CreateUserSchema(BaseModel):
    email: EmailStr
    otp: str
    role: Roles