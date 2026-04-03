from pydantic import BaseModel, ConfigDict

class CreateLayoutSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)
    
    name: str
    layout: dict
    theatre_id: int