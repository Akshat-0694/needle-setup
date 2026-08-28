import asyncio
import os

from needles.base import NeedleWorker
from core.protocol import Task

class Researcher(NeedleWorker):
    name = "researcher"

    async def handle(self, task: Task):
        question = task.payload.get("question", "").strip()
        if not question:
            await self.emit("research.failed", {"task_id": task.id, "error": "question is required"})
            return

        base_url = os.getenv("LLM_BASE_URL", "").strip()
        api_key = os.getenv("LLM_API_KEY", "").strip()
        model = os.getenv("LLM_MODEL", "").strip()

        if not (base_url and api_key and model):
            answer = (
                "Researcher is online, but no LLM is configured. "
                "Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in .env."
            )
        else:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(base_url=base_url, api_key=api_key)
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a concise research assistant. State uncertainty explicitly."},
                    {"role": "user", "content": question},
                ],
            )
            answer = response.choices[0].message.content or ""

        await self.emit("research.completed", {
            "task_id": task.id,
            "question": question,
            "answer": answer,
        })

if __name__ == "__main__":
    asyncio.run(Researcher().run())
