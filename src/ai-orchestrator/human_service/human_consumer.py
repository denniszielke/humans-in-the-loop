import asyncio
from llama_agents import (
    SimpleMessageQueue,
)

from multi_agent_app.additional_services.task_result import TaskResultService

message_queue_host =  os.getenv("MESSAGE_QUEUE_HOST")
message_queue_port =  os.getenv("MESSAGE_QUEUE_PORT")
human_consumer_host =  os.getenv("HUMAN_CONSUMER_HOST")
human_consumer_port =  os.getenv("HUMAN_CONSUMER_PORT")

# create our multi-agent framework components
message_queue = SimpleMessageQueue(
    host=message_queue_host,
    port=int(message_queue_port) if message_queue_port else None,
)
queue_client = message_queue.client


human_consumer_server = TaskResultService(
    message_queue=queue_client,
    host=human_consumer_host,
    port=int(human_consumer_port) if human_consumer_port else None,
    name="human",
)

app = human_consumer_server._app


# register to message queue
async def register_and_start_consuming() -> None:
    start_consuming_callable = await human_consumer_server.register_to_message_queue()
    await start_consuming_callable()


if __name__ == "__main__":
    asyncio.run(register_and_start_consuming())