import asyncio
import os
from dotenv import load_dotenv
from hub.bus import Bus
from core.protocol import Task, Event

load_dotenv()

class NeedleWorker:
    name = "base"

    def __init__(self):
        self.bus = Bus(os.getenv("REDIS_URL", "redis://redis:6379/0"))

    async def run(self):
        print(f"[{self.name}] online")
        while True:
            try:
                task = await self.bus.dequeue(self.name, timeout=5)
                if task:
                    await self.handle(task)
            except Exception as exc:
                print(f"[{self.name}] error: {exc}", flush=True)
                await asyncio.sleep(2)

    async def emit(self, event_type, payload):
        event = Event(type=event_type, source=self.name, payload=payload)
        await self.bus.publish(event)
        print(f"[{self.name}] EVENT {event.type}: {payload}", flush=True)

    async def handle(self, task: Task):
        raise NotImplementedError
