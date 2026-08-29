from app.integrations import notion


def search_context(query, limit=5):
    """
    Retrieve compact Notion context for use by other agents.
    """
    result = notion.search(
        query,
        page_size=limit,
    )

    if not isinstance(result, dict):
        return result

    pages = []

    for item in result.get("results", []):
        pages.append(
            {
                "id": item.get("id"),
                "url": item.get("url"),
                "object": item.get("object"),
                "properties": item.get("properties", {}),
            }
        )

    return pages
