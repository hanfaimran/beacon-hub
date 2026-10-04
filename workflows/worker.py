import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

from workflows.reminders import (
    ReminderWorkflow,
    load_dates,
    is_still_active,
    fire_reminder,
)

logging.basicConfig(level=logging.INFO)


async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="beacon",
        workflows=[ReminderWorkflow],
        activities=[load_dates, is_still_active, fire_reminder],
    )
    print("Worker running on task queue 'beacon'...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
