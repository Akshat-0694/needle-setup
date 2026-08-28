import json
import redis.asyncio as redis
from core.protocol import Task, Event

class Bus:
    def __init__(self, url: str):
        self.r = redis.from_url(url, decode_responses=True)

    async def enqueue(self, task: Task):
        await self.r.rpush(f"needle:queue:{task.needle}", task.model_dump_json())

    async def dequeue(self, needle: str, timeout=5):
        item = await self.r.blpop(f"needle:queue:{needle}", timeout=timeout)
        if not item:
            return None
        return Task.model_validate_json(item[1])

    async def publish(self, event: Event):
        await self.r.publish("needle:events", event.model_dump_json())
