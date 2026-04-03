from pydantic import BaseModel, ConfigDict

class CreateScreenSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)
    
    name: str
    theatre_id: int
    layout_id: int