from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.helper import validate_otp
from app.core.redis_config import Redis
from app.repositories.user_repository import UserRepository
from app.repositories.theatre_repository import TheatreRepository
from app.repositories.movie_repository import MovieRepository
from app.schemas.user_schema import UserOutSchema
from app.schemas.theatre_schema import TheatreOutSchema
from app.schemas.movie_schema import MovieOutSchema
from app.schemas.standard_schema import ResponseSchema, create_response
from fastapi import HTTPException, status
import httpx
from app.core.config import settings
from datetime import timedelta


class AdminService:
    """Handle admin related operations."""

    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        user_repo: UserRepository = None,
        theatre_repo: TheatreRepository = None,
        movie_repo: MovieRepository = None,
    ):
        self.db = db
        self.redis = redis
        self.user_repo = user_repo
        self.theatre_repo = theatre_repo
        self.movie_repo = movie_repo

    async def create_user_service(self, user_body: dict) -> ResponseSchema:
        """Verify OTP and create a new user with given role."""
        user_email = user_body.get("email")
        otp = user_body.get("otp")
        role = user_body.get("role")

        await validate_otp(email=user_email, otp=otp, redis=self.redis)

        async with self.db.begin():
            self.user_repo.db = self.db

            user = await self.user_repo.create_new_user_repo(
                email=user_email, role=role
            )
        user_data = UserOutSchema.model_validate(user).model_dump(mode="json")
        return create_response(
            data=user_data, message=f"User created successfully with role {role}"
        )

    async def create_theatre_service(self, theatre_body: dict) -> ResponseSchema:
        """Create a theatre and assign operator to it."""
        theatre_name = theatre_body.get("name").lower()
        operator_email = theatre_body.get("operator_email").lower()
        theatre_area = theatre_body.get("area").lower()
        theatre_city = theatre_body.get("city").lower()

        async with self.db.begin():
            self.theatre_repo.db = self.db

            new_theatre = await self.theatre_repo.create_theatre_repo(
                name=theatre_name, area=theatre_area, city=theatre_city
            )

            self.user_repo.db = self.db
            user_obj = await self.user_repo.get_user_id_by_email_and_role_repo(
                email=operator_email, role="theatre_admin"
            )

            if not user_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Theatre operator not found",
                )

            await self.theatre_repo.link_operator_to_theatre_repo(
                theatre_id=new_theatre.id, user_id=user_obj
            )

        theatre_data = TheatreOutSchema.model_validate(new_theatre).model_dump(
            mode="json"
        )
        return create_response(
            data=theatre_data, message="Theatre created successfully"
        )

    async def create_new_movie_service(self, movie_payload) -> ResponseSchema:
        """Fetch movie data from OMDB and create new movie."""

        # ---------- INPUT VALIDATION ----------
        if not movie_payload.imdb_id and not movie_payload.title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either imdb_id or title",
            )

        if movie_payload.imdb_id and movie_payload.title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide only one of imdb_id or title",
            )

        # ---------- BUILD OMDB PARAMS ----------
        params = {"apikey": settings.OMDB_API_KEY}

        if movie_payload.imdb_id:
            params["i"] = movie_payload.imdb_id
        else:
            params["t"] = movie_payload.title

        # ---------- FETCH FROM OMDB ----------
        async with httpx.AsyncClient() as client:
            response = await client.get("https://www.omdbapi.com/", params=params)

            if response.status_code != status.HTTP_200_OK:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch movie data",
                )

            data = response.json()

        if data.get("Response") == "False":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=data.get("Error", "Movie not found"),
            )

        # ---------- DB OPERATIONS ----------
        async with self.db.begin():
            self.movie_repo.db = self.db

            imdb_id = data.get("imdbID")

            movie_found = await self.movie_repo.get_movie_by_imdb_id(imdb_id)

            if movie_found:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Movie already exist",
                )

            movie = await self.movie_repo.create_new_movie_repo(
                name=data.get("Title"),
                duration=timedelta(minutes=int(data.get("Runtime").split(" ")[0])),
                description=data.get("Plot"),
                genre=data.get("Genre"),
                rating=float(data.get("imdbRating")),
                imdb_id=imdb_id,
            )

        # ---------- RESPONSE ----------
        movie_data = MovieOutSchema.model_validate(movie).model_dump(mode="json")

        return create_response(data=movie_data, message="Movie created successfully")

    async def get_all_users_service(self, page: int = 1, size: int = 10):
        """Fetch paginated list of users."""
        async with self.db.begin():
            self.user_repo.db = self.db
            users = await self.user_repo.get_all_users_repo(page, size)
            users_data = [
                UserOutSchema.model_validate(user).model_dump(mode="json")
                for user in users
            ]
        return create_response(data=users_data, message="Users fetched successfully")

    async def get_all_theatres_service(self, page: int = 1, size: int = 10):
        """Fetch paginated list of theatres."""
        async with self.db.begin():
            self.theatre_repo.db = self.db
            theatres = await self.theatre_repo.get_all_theatres_repo(page, size)
            theatres_data = [
                TheatreOutSchema.model_validate(theatre).model_dump(mode="json")
                for theatre in theatres
            ]
        return create_response(
            data=theatres_data, message="Theatres fetched successfully"
        )

    async def get_all_movies_service(self, page: int = 1, size: int = 10):
        """Fetch paginated list of movies."""
        async with self.db.begin():
            self.movie_repo.db = self.db
            movies = await self.movie_repo.get_all_movies(page, size)

            movies_data = [
                MovieOutSchema.model_validate(movie).model_dump(mode="json")
                for movie in movies
            ]
        return create_response(data=movies_data, message="Movies fetched successfully")

    async def delete_theatre_service(self, theatre_id: str):
        """Delete theatre by ID."""
        async with self.db.begin():
            self.theatre_repo.db = self.db

            theatre_details = await self.theatre_repo.delete_theatre_repo(
                theatre_id=theatre_id
            )

            theatre_data = TheatreOutSchema.model_validate(theatre_details).model_dump(
                mode="json"
            )
        return create_response(
            data=theatre_data, message="Theatre deleted successfully"
        )

    async def delete_movie_service(self, movie_id: str):
        """Delete movie by ID."""
        async with self.db.begin():
            self.movie_repo.db = self.db

            movie_details = await self.movie_repo.delete_movie_repo(movie_id=movie_id)
            movie_data = MovieOutSchema.model_validate(movie_details).model_dump(
                mode="json"
            )
        return create_response(data=movie_data, message="Movie deleted successfully")
