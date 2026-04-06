from pydantic import BaseModel, ConfigDict, EmailStr
from uuid import UUID
from enum import Enum


class Roles(str, Enum):
    USER = "user"
    ADMIN = "admin"
    THEATRE_ADMIN = "theatre_admin"


class BaseUserAuth(BaseModel):
    email: EmailStr
    otp: str
    model_config = ConfigDict(str_to_lower=True)


class UserSigninSchema(BaseUserAuth):
    """Used for standard user login."""

    pass


class CreateUserSchema(BaseUserAuth):
    """Used for user creation with role by admin."""

    role: Roles


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    role_id: UUID


class UserOutSchema(UserBase):
    id: UUID
    google_id: str | None = None
    model_config = ConfigDict(from_attributes=True)
