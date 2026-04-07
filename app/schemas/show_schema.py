from pydantic import BaseModel, ConfigDict
from datetime import datetime

class CreateShowSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)
    
    start_time: datetime
    screen_id: str
    movie_id: str
    price: dict