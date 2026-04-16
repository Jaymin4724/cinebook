from fastapi import APIRouter, status, Query
from typing import Annotated

from app.schemas.standard_schema import ResponseSchema, create_response
from app.services.search_service import search_movies_and_theatres

search_router = APIRouter(prefix="/search", tags=["search"])


@search_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
)
async def global_search_route(
    q: Annotated[
        str, Query(min_length=1, description="Search for movie or theatre name")
    ],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """Search movies and theatres with query and limit."""
    search_results = await search_movies_and_theatres(query_text=q, limit=limit)

    data = {"items": search_results, "total": len(search_results)}

    return create_response(
        data=data,
        message="Search results retrieved successfully",
    )
