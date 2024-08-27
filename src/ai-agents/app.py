import os
import asyncio
import dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from llama_agents.message_queues.apache_kafka import KafkaMessageQueue

dotenv.load_dotenv()

from llama_index.llms.azure_openai import AzureOpenAI

from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_agents import AgentService

import logging
import sys

logging.basicConfig(
    stream=sys.stdout, level=logging.WARNING
)  # logging.DEBUG for more verbose output
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

from llama_index.core import Settings

kafka_connection_url = os.getenv("KAFKA_URL")
control_plane_host = os.getenv("CONTROL_PLANE_HOST")
control_plane_port = os.getenv("CONTROL_PLANE_PORT")
tools_agent_host = os.getenv("AGENT_HOST")
tools_agent_port = os.getenv("AGENT_PORT")

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

import time

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    WARNING = '\033[92m'
    ENDC = '\033[0m'

# create an agent
def get_machine_status() -> str:
    """Returns information about the production machine"""
    print(f"{bcolors.WARNING}#### Returning machine status from tool...{bcolors.ENDC}")
    time.sleep(10)
    print(f"{bcolors.WARNING}#### Returned machine status from tool{bcolors.ENDC}")
    return "The machine is healthy."
def get_number_of_machine_jobs() -> str:
    """Returns information about the number of jobs on the production machine"""
    print(f"{bcolors.WARNING}#### Returning number of machine jobs from tool...{bcolors.ENDC}")
    time.sleep(10)
    print(f"{bcolors.WARNING}#### Returned number of machine jobs from too{bcolors.ENDC}")
    return "The machine has 5 jobs."

def get_order_status() -> str:
    """Returns information about the current order status"""
    print(f"{bcolors.WARNING}#### Returning order status from tool...{bcolors.ENDC}")
    time.sleep(10)
    print(f"{bcolors.WARNING}#### Returned order status from tool{bcolors.ENDC}")
    return "There are two new orders in the system."

machine_tools_1 = FunctionTool.from_defaults(fn=get_machine_status)
machine_tools_2 = FunctionTool.from_defaults(fn=get_number_of_machine_jobs)
order_tools_1 = FunctionTool.from_defaults(fn=get_order_status)

agent1 = ReActAgent.from_tools([machine_tools_1, machine_tools_2, order_tools_1], llm=llm)

message_queue = KafkaMessageQueue(url=kafka_connection_url)

agent_server = AgentService(
    agent=agent1,
    message_queue=message_queue,
    description="Useful for getting information about machines and orders.",
    service_name="order_machine_agent",
    host=tools_agent_host,
    port=int(tools_agent_port) if tools_agent_port else None,
)

app = agent_server._app

# registration
async def register_and_start_consuming() -> None:
    # register to message queue
    start_consuming_callable = await agent_server.register_to_message_queue()
    # register to control plane
    await agent_server.register_to_control_plane(
        control_plane_url=(
            f"http://{control_plane_host}:{control_plane_port}"
            if control_plane_port
            else f"http://{control_plane_host}"
        )
    )
    # start consuming
    await start_consuming_callable()

if __name__ == "__main__":
    asyncio.run(register_and_start_consuming())
