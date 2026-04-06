from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.helper import validate_otp
from app.core.redis_config import Redis
from app.repositories.user_repository import UserRepository
from app.repositories.theatre_repository import TheatreRepository
from app.repositories.movie_repository import MovieRepository
from app.schemas.standard_schema import ResponseSchema, create_response
from fastapi import HTTPException, status
import httpx
from app.core.config import settings
from datetime import timedelta


class AdminService:
    
    def __init__(
        self, 
        db: AsyncSession,
        redis: Redis,
        user_repo: UserRepository = None,
        theatre_repo: TheatreRepository = None,
        movie_repo: MovieRepository = None
    ):
        self.db = db
        self.redis = redis
        self.user_repo = user_repo
        self.theatre_repo = theatre_repo
        self.movie_repo = movie_repo


    async def create_user_service(self, user_body: dict) -> ResponseSchema:

        user_email = user_body.get("email")
        otp = user_body.get("otp")
        role = user_body.get("role")
        
        await validate_otp(
            email=user_email,
            otp=otp,
            redis=self.redis
        )

        async with self.db.begin():
            self.user_repo.db = self.db

            await self.user_repo.create_new_user_repo(
                email=user_email,
                role=role
            )

        return create_response(message=f"User created successfully with role {role}")
        

    async def create_theatre_service(self, theatre_body: dict) -> ResponseSchema:
        
        theatre_name = theatre_body.get("name").lower()
        operator_email = theatre_body.get("operator_email").lower()
        theatre_area = theatre_body.get("area").lower()
        theatre_city = theatre_body.get("city").lower()

        async with self.db.begin():
            self.theatre_repo.db = self.db

            new_theatre = await self.theatre_repo.create_theatre_repo(
                name=theatre_name,
                area=theatre_area,
                city=theatre_city
            )

            self.user_repo.db = self.db
            user_obj = await self.user_repo.get_user_id_by_email_and_role_repo(
                email=operator_email,
                role="theatre_admin"
            )

            if not user_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="Theatre operator not found"
                )
                
            await self.theatre_repo.link_operator_to_theatre_repo(
                theatre_id=new_theatre.id,
                user_id=user_obj
            )

        return create_response(
            message="Theatre created successfully"
        )
    

    async def create_new_movie_service(self, imdb_id: int) -> ResponseSchema:

        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://www.omdbapi.com/?i={imdb_id}&apikey={settings.OMDB_API_KEY}")
            data = response.json()

        if data.get("Response") == False:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
        
        async with self.db.begin():
            self.movie_repo.db = self.db

            movie_found = await self.movie_repo.get_movie_by_imdb_id(
                imdb_id=data.get("imdbID")
            )

            if movie_found:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Movie already exist")

            await self.movie_repo.create_new_movie_repo(
                name=data.get("Title"),
                duration=timedelta(minutes=int(data.get("Runtime").split(" ")[0])),
                description=data.get("Plot"),
                genre=data.get("Genre"),
                rating=float(data.get("imdbRating")),
                imdb_id=data.get("imdbID")
            )
        
        return create_response(message="Movie created successfully")
