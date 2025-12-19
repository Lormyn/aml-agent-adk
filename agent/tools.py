import os
from dotenv import load_dotenv
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from google.adk.tools.application_integration_tool.application_integration_toolset import ApplicationIntegrationToolset
from google.genai.types import Part, Blob
from google.adk.tools import FunctionTool
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from fpdf import FPDF
from typing import Dict, Any
import google.auth
from google.auth.transport.requests import Request

load_dotenv()

# =============================================================================
# Authentication Configuration
# =============================================================================

def is_running_locally() -> bool:
    """Detect if we're running locally vs deployed to Agent Engine."""
    # Agent Engine sets specific env vars; check for their absence
    return os.getenv("K_SERVICE") is None  # K_SERVICE is set in Cloud Run


def get_adc_token() -> str:
    """Get OAuth token from Application Default Credentials for local dev."""
    credentials, _ = google.auth.default()
    credentials.refresh(Request())
    if credentials.token is None:
        raise ValueError(
            "Failed to get ADC token. Run 'gcloud auth application-default login'."
        )
    return credentials.token


def mcp_auth_header_provider(context: ToolContext) -> dict:
    """
    Provide authentication headers for MCP Toolbox requests.
    
    - Local dev: Uses ADC token in Authorization header
    - Deployed: Returns empty dict (Agent Engine uses service account auth)
    """
    if is_running_locally():
        token = get_adc_token()
        return {"Authorization": f"Bearer {token}"}
    return {}


# =============================================================================
# MCP Toolset Configuration
# =============================================================================

mcp_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=os.getenv('MCP_URL')
    ),
    header_provider=mcp_auth_header_provider,
)


# =============================================================================
# PDF Generation Tool
# =============================================================================

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


# =============================================================================
# Integration Tool
# =============================================================================
integration_tool = ApplicationIntegrationToolset(
        project=os.getenv('GOOGLE_CLOUD_PROJECT'),
        location=os.getenv('GOOGLE_CLOUD_LOCATION'),
        integration="sendEmail",
        triggers=["api_trigger/send_email"],
        tool_instructions="Usable to send an email of a conversation."
    )
