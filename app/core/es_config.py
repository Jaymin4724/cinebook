from elasticsearch import AsyncElasticsearch
from app.core.config import settings

es = AsyncElasticsearch(settings.ES_URL)


async def create_index():
    index_name = "booking_search"

    if await es.indices.exists(index=index_name):
        print(f"Index '{index_name}' already exists.")
        return

    body = {
        "mappings": {
            "properties": {
                "name": {"type": "text", "analyzer": "standard"},
                "type": {"type": "keyword"},
                "db_id": {"type": "keyword"},
            }
        }
    }

    await es.indices.create(index=index_name, body=body, ignore=400)
    print(f"Index '{index_name}' created.")
