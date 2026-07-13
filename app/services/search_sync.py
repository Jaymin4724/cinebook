import logging
from fastapi import BackgroundTasks
from app.models import MovieModel, TheatreModel
from app.core.es_config import es

logger = logging.getLogger(__name__)


async def async_sync_to_es(instance_data: dict) -> None:
    """Sync movie or theatre data to Elasticsearch index."""
    index_name = "booking_search"
    model_type = instance_data["type"]
    doc_id = f"{model_type}_{instance_data['id']}"

    try:
        if instance_data.get("is_hidden"):
            await es.options(ignore_status=[404]).delete(index=index_name, id=doc_id)
            return

        doc = {
            "name": instance_data["name"],
            "type": model_type,
            "db_id": str(instance_data["id"]),
        }
        await es.index(index=index_name, id=doc_id, body=doc)
    except Exception:
        logger.exception("Failed to sync %s to Elasticsearch", doc_id)


def queue_search_sync(background_tasks: BackgroundTasks, target) -> None:
    """Queue a background Elasticsearch sync for a movie/theatre row, after it commits."""
    instance_data = {
        "id": target.id,
        "name": target.name,
        "type": "movie" if isinstance(target, MovieModel) else "theatre",
        "is_hidden": getattr(target, "is_deleted", False)
        or not getattr(target, "is_active", True),
    }
    background_tasks.add_task(async_sync_to_es, instance_data)
