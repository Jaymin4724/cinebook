import asyncio
from sqlalchemy import event
from app.models import MovieModel, TheatreModel
from app.core.es_config import es


async def async_sync_to_es(instance_data):
    index_name = "booking_search"
    model_type = instance_data["type"]
    doc_id = f"{model_type}_{instance_data['id']}"

    if instance_data.get("is_hidden"):
        await es.delete(index=index_name, id=doc_id, ignore=[404])
        return

    doc = {
        "name": instance_data["name"],
        "type": model_type,
        "db_id": str(instance_data["id"]),
    }
    await es.index(index=index_name, id=doc_id, body=doc)


def sync_to_es_wrapper(target):
    instance_data = {
        "id": target.id,
        "name": target.name,
        "type": "movie" if isinstance(target, MovieModel) else "theatre",
        "is_hidden": getattr(target, "is_deleted", False)
        or not getattr(target, "is_active", True),
    }

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(async_sync_to_es(instance_data))
    except RuntimeError:
        asyncio.run(async_sync_to_es(instance_data))


def handle_after_save(mapper, connection, target):
    sync_to_es_wrapper(target)


event.listen(MovieModel, "after_insert", handle_after_save)
event.listen(MovieModel, "after_update", handle_after_save)

event.listen(TheatreModel, "after_insert", handle_after_save)
event.listen(TheatreModel, "after_update", handle_after_save)
