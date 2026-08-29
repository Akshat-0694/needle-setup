import os
import asyncio
import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.config import settings


NOTION_MCP_URL = settings.notion_mcp_url


def _extract(result):
    """
    Convert an MCP CallToolResult into JSON/text that Needle can consume.
    """
    if getattr(result, "is_error", False):
        raise RuntimeError(
            f"Notion MCP tool failed: {result.content}"
        )

    if getattr(result, "structured_content", None):
        return result.structured_content

    content = getattr(result, "content", [])

    texts = []

    for item in content:
        text = getattr(item, "text", None)

        if text is not None:
            texts.append(text)

    if len(texts) == 1:
        text = texts[0]

        try:
            import json
            return json.loads(text)
        except Exception:
            return text

    return "\n".join(texts)


async def _call_tool(tool_name, arguments=None):
    token = settings.notion_mcp_auth_token

    if not token:
        raise RuntimeError(
            "NOTION_MCP_AUTH_TOKEN is not set"
        )

    async with httpx.AsyncClient(
        headers={
            "Authorization": "Bearer " + token,
        }
    ) as http_client:

        async with streamable_http_client(
            NOTION_MCP_URL,
            http_client=http_client,
        ) as (read_stream, write_stream):

            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:

                await session.initialize()

                result = await session.call_tool(
                    tool_name,
                    arguments or {},
                )

                return _extract(result)


def _call(tool_name, arguments=None):
    """
    Synchronous interface for the rest of Needle.
    """
    return asyncio.run(
        _call_tool(
            tool_name,
            arguments,
        )
    )


def search(query, page_size=20):
    """
    Search accessible Notion pages/data sources by title.
    """
    return _call(
        "API-post-search",
        {
            "query": query,
            "page_size": page_size,
        },
    )


def get_page(page_id):
    """
    Retrieve a Notion page.
    """
    return _call(
        "API-retrieve-a-page",
        {
            "page_id": page_id,
        },
    )


def get_page_markdown(page_id):
    """
    Retrieve a Notion page as Markdown.
    """
    return _call(
        "API-retrieve-page-markdown",
        {
            "page_id": page_id,
        },
    )


def create_page(
    parent_page_id,
    title,
    markdown="",
):
    """
    Create a child page under an existing Notion page.
    """
    properties = {
        "title": {
            "title": [
                {
                    "text": {
                        "content": title,
                    }
                }
            ]
        }
    }

    arguments = {
        "parent": {
            "page_id": parent_page_id,
        },
        "properties": properties,
    }

    if markdown:
        arguments["markdown"] = markdown

    return _call(
        "API-post-page",
        arguments,
    )


def update_page_markdown(
    page_id,
    markdown,
):
    """
    Replace/update a Notion page's content using Markdown.
    """
    return _call(
        "API-update-page-markdown",
        {
            "page_id": page_id,
            "markdown": markdown,
        },
    )


def append_blocks(page_id, children):
    """
    Append Notion block children to an existing page.
    """
    return _call(
        "API-patch-block-children",
        {
            "block_id": page_id,
            "children": children,
        },
    )


def list_page_blocks(page_id):
    """
    Retrieve the blocks belonging to a page.
    """
    return _call(
        "API-get-block-children",
        {
            "block_id": page_id,
        },
    )
