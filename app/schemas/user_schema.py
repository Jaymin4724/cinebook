from pydantic import BaseModel, ConfigDict, EmailStr, field_serializer
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


class RoleOutSchema(BaseModel):
    role: str
    model_config = ConfigDict(from_attributes=True)


class UserDetailOutSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    mobile_no: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserOutSchema(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool = True
    role: RoleOutSchema
    google_id: str | None = None
    user_detail: UserDetailOutSchema | None = None
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("role")
    def serialize_role(self, role):
        return role.role if role else None

    @staticmethod
    def remove_none(data: dict):
        cleaned_data = {}

        for key, value in data.items():
            if value is not None:
                cleaned_data[key] = value

        return cleaned_data

    @field_serializer("user_detail")
    def serialize_user_detail(self, detail):
        if not detail:
            return None

        data = self.remove_none(
            {
                "first_name": detail.first_name,
                "last_name": detail.last_name,
                "mobile_no": detail.mobile_no,
            }
        )

        return data if data else None
