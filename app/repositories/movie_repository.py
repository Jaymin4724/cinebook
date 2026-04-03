from sqlalchemy.ext.asyncio import AsyncSession
from app.models import MovieModel
from datetime import timedelta
from sqlalchemy import select


class MovieRepository:

    def __init__(self, db: AsyncSession):
        self.db = db
        

    async def create_new_movie_repo(
        self,
        name: str,
        duration: timedelta,
        description: str,
        rating: float,
        genre: str,
        imdb_id: str
    ) -> MovieModel:
        
        new_movie = MovieModel(
            name=name,
            duration=duration,
            description=description,
            rating=rating,
            genre=genre,
            imdb_id=imdb_id
        )

        self.db.add(new_movie)

        await self.db.flush()

        return new_movie
    
    async def get_movie_by_imdb_id(
        self,
        imdb_id: str
    ) -> MovieModel:
        
        query = select(
            MovieModel
        ).where(
            MovieModel.imdb_id == imdb_id
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()