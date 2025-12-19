from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.memory import VertexAiMemoryBankService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
import os

from .tools import mcp_tools, pdf_tool, integration_tool
from .config import get_sar_agent_instruction, get_root_agent_instruction

load_dotenv()

# In-memory artifact service for PDF storage
artifact_service = InMemoryArtifactService()

# Memory Bank service for persistent memory storage
memory_bank_service = VertexAiMemoryBankService(
    project=os.getenv('GOOGLE_CLOUD_PROJECT'),
    location=os.getenv('GOOGLE_CLOUD_LOCATION'),
    agent_engine_id=os.getenv('AGENT_ENGINE_ID'),
)

# Callback to auto-save session to memory after each interaction
async def auto_save_to_memory_callback(callback_context):
    await memory_bank_service.add_session_to_memory(
        callback_context._invocation_context.session
    )
    print("\n****Triggered memory generation****\n")


#Agent Definitions
sar_agent = Agent(
    model='gemini-3-flash-preview',
    name='sar_agent',
    instruction=get_sar_agent_instruction(),
    tools=[mcp_tools, pdf_tool, integration_tool],
)

root_agent = Agent(
    model='gemini-3-flash-preview',
    name='aml_agent',
    instruction=get_root_agent_instruction(),
    tools=[PreloadMemoryTool(), mcp_tools],
    after_agent_callback=auto_save_to_memory_callback,
    sub_agents=[sar_agent],
    )