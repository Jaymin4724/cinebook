import logging

from elasticsearch import AsyncElasticsearch
from app.core.config import settings

logger = logging.getLogger(__name__)

es = AsyncElasticsearch(settings.ES_URL, verify_certs=False)


async def create_index():
    """Create Elasticsearch index for search if not exists."""
    index_name = "booking_search"

    if await es.indices.exists(index=index_name):
        logger.info("Index '%s' already exists.", index_name)
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
    logger.info("Index '%s' created.", index_name)
