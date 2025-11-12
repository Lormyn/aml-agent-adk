from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.application_integration_tool.application_integration_toolset import ApplicationIntegrationToolset
from google.genai.types import Part, Blob
from google.adk.tools import FunctionTool, BaseTool
from typing import Dict, Any
from fpdf import FPDF
from google.adk.runners import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.adk.memory import VertexAiMemoryBankService
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.tool_context import ToolContext
import google.auth
from google.auth.transport.requests import Request
import os
import datetime
load_dotenv()


# OAuth Configuration
OAUTH_KEY = "temp:token"

def get_token_from_adc():
    """ Function to get OAuth token from ADC when running locally (adk web)"""
    #scopes = ["https://www.googleapis.com/auth/bigquery"]
    credentials, project_id = google.auth.default()
    
    # Force a refresh to get a valid access token.
    credentials.refresh(Request())
    oauth_token = credentials.token

    # A quick check to make sure the token isn't None
    if oauth_token is None:
        raise ValueError("Failed to retrieve OAuth token from ADC. "
                        "Make sure you have run 'gcloud auth application-default login'.")
    return oauth_token

def check_token(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext): 
    """Before tool callback to check for OAuth token in context"""

    oauth_token = tool_context.state.get(OAUTH_KEY)
    
    if OAUTH_KEY == "temp:token":
        # local run, add token from adc
        tool_context.state[OAUTH_KEY] = get_token_from_adc()

    return None

def get_token_from_context(context: ToolContext):
    oauth_token = context.state.get(OAUTH_KEY)
    return {"Authorization": f"Bearer {oauth_token}"}


# MCP Toolset configuration
port = os.getenv("PORT", "8080")
mcp_tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url = os.getenv('MCP_URL')
    ),
    header_provider=get_token_from_context,
)

# Function to generate valid PDF bytes from text content
def generate_valid_pdf_bytes(text_content: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text_content)
    return pdf.output(dest='S')

async def create_pdf_file(
    content_to_save: str,
    filename: str,
    tool_context: CallbackContext = None,
) -> Dict[str, Any]:
    """
    Creates a downloadable PDF report from content and saves it as an ADK Artifact 
    for the user.

    Args:
        content_to_save: The full text content of the report to be saved into the PDF.
        filename: The desired name for the PDF file (e.g., 'SAR_Report_123.pdf').
        tool_context: The ADK context object provided by the framework.
    
    Returns:
        A structured dictionary indicating success and providing the download link.
    """
    if tool_context is None:
        return {"status": "error", "message": "Tool context is missing."}

    # 1. Convert text to PDF bytes
    pdf_bytes = generate_valid_pdf_bytes(content_to_save)

    # 2. Create the ADK Artifact (types.Part)
    artifact_part = Part(
        inline_data=Blob(data=pdf_bytes, mime_type="report/pdf")
    )

    # 3. Save the Artifact to the ADK System
    version = await tool_context.save_artifact(
        filename=filename,
        artifact=artifact_part,
    )

    # 4. Return structured response (ADK UI intercepts this)
    return {
        "status": "success",
        "message": f"Artifact saved. File name: '{filename}' (version {version}) has been created and is now available for download.",
        "filename": filename,
    }

# Wrap the function as an ADK tool
pdf_tool = FunctionTool(
    func=create_pdf_file,
)



# Application Integration Tool for sending emails
integration_tool = ApplicationIntegrationToolset(
        project=os.getenv('GOOGLE_CLOUD_PROJECT'),
        location=os.getenv('GOOGLE_CLOUD_LOCATION'),
        integration="sendEmail",
        triggers=["api_trigger/send_email"],
        tool_instructions="Usable to send an email of a conversation."
    )

# In-memory artifact service for PDF storage
artifact_service = InMemoryArtifactService()


# Callback to auto-save session to memory after each interaction
async def auto_save_session_to_memory_callback(callback_context: CallbackContext):
    if (
        callback_context._invocation_context.memory_service is not None
        and callback_context._invocation_context.session is not None
    ):
        await callback_context._invocation_context.memory_service.add_session_to_memory(
            callback_context._invocation_context.session
        )


#Agent Definitions
sar_agent = Agent(
    model='gemini-2.5-flash',
    name='sar_agent',
    instruction=f"""Today's date is {datetime.datetime.now().strftime("%Y-%m-%d")}.
    You are a specialist AML analyst for Swedish Bank AB. Your sole purpose is to write a detailed
    and comprehensive Suspicious Activity Report (SAR) narrative.

    YOUR PROCESS MUST BE:
    1. **IDENTIFY USER:** Extract the specific User ID mentioned in the current request (e.g., 'U-HR-005').
    2. **INVESTIGATE:** Use the 'mcp_tools' to look up all necessary information about the extracted User ID. Gather all relevant details.
    3. **DRAFT NARRATIVE:** Based on the investigation, write the complete, final, and detailed SAR narrative.
    4. **OUTPUT:** Once the narrative is complete, you **MUST** output the report in text first. Then, explicitly ask the user if they want to download the report as a PDF.
    5. **CONFIRMATION & GENERATION:** If, and only if, the user explicitly confirms that they want the PDF, you must use the 'pdf_tool' one time to generate the PDF.
    * The 'content_to_save' argument **MUST** be the full SAR narrative drafted in step 3.
    * The 'filename' argument **MUST** use the extracted User ID and today's date, following the format: 'SAR_Report_[USER_ID]_[TODAYSDATE].pdf'.
    """,
    tools=[mcp_tools, pdf_tool],
)

root_agent = Agent(
    model='gemini-2.5-flash',
    name='aml_agent',
    instruction=f"""Today's date is {datetime.datetime.now().strftime("%Y-%m-%d")}.
    You are an AML analyst's assistant for Swedish Bank AB. Your job is to perform initial investigations
    using the available tools to look up user information. 

    If the user does not specifically ask for something else, start the conversation by saying: "Hi, I am your AML assistant. How can I help you today?" 

    Present your findings to the analyst. Do not draft a report on your own.

    If the analyst explicitly asks you to draft a SAR report, then and only then,
    send the task over to the 'sar_agent' sub-agent to handle the SAR drafting and PDF generation.
    """,
    tools=[PreloadMemoryTool(), mcp_tools, integration_tool],
    after_agent_callback=auto_save_session_to_memory_callback,
    before_tool_callback=check_token,
    sub_agents=[sar_agent],
    )

# Memory service for session persistence in Memory Bank
memory_service = VertexAiMemoryBankService(
    project=os.getenv('GOOGLE_CLOUD_PROJECT'),
    location=os.getenv('GOOGLE_CLOUD_LOCATION'),
    agent_engine_id=os.getenv('AGENT_ENGINE_ID')
)

# Runner setup
app_runner = Runner(
   app_name='aml_agent',
    agent=root_agent,
    session_service=InMemorySessionService(),
    memory_service=memory_service,
    artifact_service=artifact_service,
)