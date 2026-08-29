import asyncio
import json

from mcp import Client


MCP_URL = "http://mcp:9000/mcp"


def normalize(value):
    if value is None:
        return None

    if isinstance(value, (list, tuple)):
        return [normalize(x) for x in value]

    if isinstance(value, dict):
        # MCP wrapper produced by our server/client path.
        if set(value.keys()) == {"result"}:
            return normalize(value["result"])

        if "structuredContent" in value:
            return normalize(value["structuredContent"])

        if "result" in value and len(value) <= 2:
            return normalize(value["result"])

        return {
            key: normalize(val)
            for key, val in value.items()
        }

    if isinstance(value, str):
        text = value.strip()

        try:
            decoded = json.loads(text)
            return normalize(decoded)
        except (json.JSONDecodeError, TypeError):
            return value

    return value


async def _call(name: str, arguments: dict):
    async with Client(MCP_URL) as client:

        result = await client.call_tool(
            name,
            arguments,
        )

        if result.is_error:
            raise RuntimeError(str(result.content))

        if result.structured_content is not None:
            return normalize(result.structured_content)

        values = []

        for item in result.content:

            text = getattr(item, "text", None)

            if text is not None:
                values.append(text)
            else:
                values.append(str(item))

        if len(values) == 1:
            return normalize(values[0])

        return normalize(values)


def call(name: str, **arguments):
    return asyncio.run(
        _call(name, arguments)
    )
