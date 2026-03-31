from pydantic import BaseModel, EmailStr

class UserSigninSchema(BaseModel):
    email: EmailStr
    otp: str