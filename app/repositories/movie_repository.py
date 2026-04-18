from sqlalchemy.ext.asyncio import AsyncSession
from app.models import MovieModel, ShowModel, ScreenModel
from datetime import timedelta
from sqlalchemy import select
from datetime import datetime, timezone
from fastapi import HTTPException, status


class MovieRepository:
    """Handle database operations related to movies."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_new_movie_repo(
        self,
        name: str,
        duration: timedelta,
        description: str,
        rating: float,
        genre: str,
        imdb_id: str,
    ) -> MovieModel:
        """Create a new movie record."""
        new_movie = MovieModel(
            name=name,
            duration=duration,
            description=description,
            rating=rating,
            genre=genre,
            imdb_id=imdb_id,
        )

        self.db.add(new_movie)

        await self.db.flush()

        return new_movie

    async def get_movie_by_imdb_id(self, imdb_id: str) -> MovieModel:
        """Fetch movie by IMDB ID."""
        query = select(MovieModel).where(MovieModel.imdb_id == imdb_id)

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_all_movies(self, page: int, size: int):
        """Fetch paginated list of active movies."""
        skip = (page - 1) * size
        result = await self.db.scalars(
            select(MovieModel)
            .where(MovieModel.is_deleted == False)
            .offset(skip)
            .limit(size)
        )
        return result.all()

    async def get_movie_by_id(self, movie_id: str):
        """Fetch movie by ID if not deleted."""
        query = select(MovieModel).where(
            MovieModel.id == movie_id, MovieModel.is_deleted == False
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_movies_by_theatre_repo(
        self, theatre_id: str, page: int, size: int
    ) -> list[MovieModel]:
        """Fetch movies running in a theatre with upcoming shows."""
        skip = (page - 1) * size

        query = (
            select(MovieModel)
            .join(ShowModel, ShowModel.movie_id == MovieModel.id)
            .join(ScreenModel, ScreenModel.id == ShowModel.screen_id)
            .where(
                ScreenModel.theatre_id == theatre_id,
                MovieModel.is_deleted == False,
                ShowModel.is_deleted == False,
                ShowModel.start_time > datetime.now(timezone.utc).replace(tzinfo=None),
            )
            .distinct()
            .offset(skip)
            .limit(size)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_movie_repo(self, movie_id: str):
        """Soft delete movie by ID if exists."""
        query = select(MovieModel).where(
            MovieModel.id == movie_id, MovieModel.is_deleted == False
        )

        result = await self.db.execute(query)

        movie_found = result.scalar_one_or_none()

        if not movie_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
            )

        return await movie_found.soft_delete(db=self.db)
