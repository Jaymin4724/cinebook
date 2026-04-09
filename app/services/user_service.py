from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis_config import Redis
from app.repositories.movie_repository import MovieRepository
from app.repositories.theatre_repository import TheatreRepository

from app.repositories.show_repository import ShowRepository
from app.schemas.movie_schema import MovieOutSchema
from app.schemas.theatre_schema import TheatreOutSchema
from app.schemas.standard_schema import ResponseSchema, create_response
from app.schemas.show_schema import ShowDetailOutSchema
from fastapi import status, HTTPException


class UserService:
    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        movie_repo: MovieRepository,
        theatre_repo: TheatreRepository,
        show_repo: ShowRepository,
    ):
        self.db = db
        self.redis = redis
        self.movie_repo = movie_repo
        self.theatre_repo = theatre_repo
        self.show_repo = show_repo

    async def get_movies_by_theatre_service(
        self, theatre_id: str, page: int = 1, size: int = 10
    ) -> ResponseSchema:
        """Fetch all movies currently showing in a specific theatre."""
        async with self.db.begin():
            self.movie_repo.db = self.db
            movies = await self.movie_repo.get_movies_by_theatre_repo(
                theatre_id=theatre_id, page=page, size=size
            )

        movies_data = [
            MovieOutSchema.model_validate(movie).model_dump(mode="json")
            for movie in movies
        ]
        return create_response(
            data=movies_data,
            message="Movies for the specified theatre fetched successfully",
        )

    async def get_theatres_by_movie_service(
        self, movie_id: str, page: int = 1, size: int = 10
    ) -> ResponseSchema:
        """Fetch all theatres that are currently screening a specific movie."""
        async with self.db.begin():
            self.theatre_repo.db = self.db
            theatres = await self.theatre_repo.get_theatres_by_movie_repo(
                movie_id=movie_id, page=page, size=size
            )

        theatres_data = [
            TheatreOutSchema.model_validate(theatre).model_dump(mode="json")
            for theatre in theatres
        ]
        return create_response(
            data=theatres_data,
            message="Theatres screening this movie fetched successfully",
        )

    async def get_shows_service(
        self, theatre_id: str, movie_id: str, page: int = 1, size: int = 10
    ) -> ResponseSchema:
        """Fetch all specific show timings for a movie at a particular theatre."""
        async with self.db.begin():
            self.show_repo.db = self.db
            shows = await self.show_repo.get_shows_repo(
                theatre_id=theatre_id, movie_id=movie_id, page=page, size=size
            )

        shows_data = [
            ShowDetailOutSchema.model_validate(show).model_dump(mode="json")
            for show in shows
        ]

        return create_response(
            data=shows_data,
            message="Available shows for this movie and theatre fetched successfully",
        )

    async def get_show_details_service(self, show_id: str) -> ResponseSchema:
        async with self.db.begin():
            self.show_repo.db = self.db
            show = await self.show_repo.get_show_by_id_repo(
                show_id=show_id, redis=self.redis
            )

            if not show:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Show not found or unavailable",
                )

        return create_response(data=show, message="Show details fetched successfully")
