from pydantic import BaseModel, EmailStr, ConfigDict

class CreateMovieSchema(BaseModel):
    model_config = ConfigDict(str_to_lower=True)
    
    name: str
    duration: int
    description: str
    rating: float
    genre: str
    imdb_id: str