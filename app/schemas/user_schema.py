from pydantic import BaseModel, EmailStr, ConfigDict

class UserSigninSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)

    email: EmailStr
    otp: str