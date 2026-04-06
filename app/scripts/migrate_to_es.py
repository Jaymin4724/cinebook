import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models import MovieModel, TheatreModel
from app.core.es_config import es
from elasticsearch.helpers import async_bulk


async def migrate_data():
    async with AsyncSessionLocal() as session:
        index_name = "booking_search"
        actions = []

        # 1. Fetch Active Movies
        movie_query = select(MovieModel).where(MovieModel.is_deleted == False)
        movie_result = await session.execute(movie_query)
        for movie in movie_result.scalars().all():
            actions.append(
                {
                    "_index": index_name,
                    "_id": f"movie_{movie.id}",
                    "_source": {
                        "name": movie.name,
                        "type": "movie",
                        "db_id": str(movie.id),
                    },
                }
            )

        # 2. Fetch Active Theatres
        theatre_query = select(TheatreModel).where(TheatreModel.is_active == True)
        theatre_result = await session.execute(theatre_query)
        for theatre in theatre_result.scalars().all():
            actions.append(
                {
                    "_index": index_name,
                    "_id": f"theatre_{theatre.id}",
                    "_source": {
                        "name": theatre.name,
                        "type": "theatre",
                        "db_id": str(theatre.id),
                    },
                }
            )

        # 3. Perform Async Bulk Indexing
        if actions:
            success, _ = await async_bulk(es, actions)
            print(f"Successfully migrated {success} items.")
        else:
            print("No records found.")


if __name__ == "__main__":
    asyncio.run(migrate_data())
