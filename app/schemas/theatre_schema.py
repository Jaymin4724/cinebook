from pydantic import BaseModel, EmailStr, ConfigDict

class CreateTheatreSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)
    
    name: str
    operator_email: EmailStr
    area: str
    city: str