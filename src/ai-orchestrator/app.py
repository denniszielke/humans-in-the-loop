import os
import asyncio
import logging
import sys
import dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from llama_agents.message_queues.apache_kafka import KafkaMessageQueue

from llama_agents import (
    AgentService,
    AgentOrchestrator,
    ControlPlaneServer,
    ServerLauncher, 
    CallableMessageConsumer
)

from llama_index.llms.azure_openai import AzureOpenAI

from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool

dotenv.load_dotenv()

logging.basicConfig(
    stream=sys.stdout, level=logging.WARNING
)  # logging.DEBUG for more verbose output
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

from llama_index.core import Settings

kafka_connection_url = os.getenv("KAFKA_URL")
control_plane_host = os.getenv("CONTROL_PLANE_HOST")
control_plane_port = os.getenv("CONTROL_PLANE_PORT")

llm: AzureOpenAI = None
if "AZURE_OPENAI_API_KEY" in os.environ:
    llm = AzureOpenAI(
        model=os.getenv("AZURE_OPENAI_COMPLETION_MODEL"),
        azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION")
    )

else:
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    llm = AzureOpenAI(
        azure_ad_token_provider=token_provider,
        use_azure_ad=True,
        model=os.getenv("AZURE_OPENAI_COMPLETION_MODEL"),
        azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
        api_key=token_provider(),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION")
    )

Settings.llm = llm

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    WARNING = '\033[92m'
    ENDC = '\033[0m'

message_queue = KafkaMessageQueue(url=kafka_connection_url)

# setup control plane
control_plane = ControlPlaneServer(
    message_queue=message_queue,
    orchestrator=AgentOrchestrator(llm=llm),
    host=control_plane_host,
    port=int(control_plane_port) if control_plane_port else None,
)

async def register_and_start_consuming() -> None:
    # register to message queue
    start_consuming_callable = await control_plane.register_to_message_queue()
    await start_consuming_callable()

# launch it
launcher = ServerLauncher(
    [],
    control_plane,
    message_queue,
    additional_consumers=[],
)

asyncio.run(register_and_start_consuming())


if __name__ == "__main__":
    launcher.launch_servers()