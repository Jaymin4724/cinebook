from app.core.es_config import es


async def search_movies_and_theatres(query_text: str, limit: int = 10):
    """
    Searches for movies and theatres by name using fuzzy matching.
    """
    index_name = "booking_search"

    search_query = {
        "query": {
            "match_phrase_prefix": {"name": {"query": query_text, "max_expansions": 10}}
        },
        "size": limit,
    }

    try:
        response = await es.search(index=index_name, body=search_query)
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append(
                {
                    "name": source["name"],
                    "type": source["type"],  # 'movie' or 'theatre'
                    "db_id": source["db_id"],  # The UUID from your DB
                    "score": hit["_score"],  # How well it matched (relevance)
                }
            )

        return results

    except Exception as e:
        print(f"Error searching Elasticsearch: {e}")
        return []
