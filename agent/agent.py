from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.adk.tools.application_integration_tool.application_integration_toolset import ApplicationIntegrationToolset
from google.genai.types import Part, Blob
from google.adk.tools import FunctionTool, BaseTool
from typing import Dict, Any
from fpdf import FPDF
from google.adk.memory import VertexAiMemoryBankService
from google.adk.artifacts import InMemoryArtifactService
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
    model='gemini-2.5-flash',
    name='sar_agent',
    instruction=f"""Today's date is {datetime.datetime.now().strftime("%Y-%m-%d")}.
    You are a specialist AML analyst for Swedish Bank AB. Your sole purpose is to write a detailed
    and comprehensive Suspicious Activity Report (SAR) narrative.

    YOUR PROCESS MUST BE:
    1. **IDENTIFY USER:** Extract the specific user name mentioned in the current request.
    2. **GATHER KYC:** Use `search-user-by-name` to fetch the user's full profile.
    3. **INVESTIGATE:** Use `trace-money-flow` and `analyze-counterparties` to find the source and destination of funds.
    4. **DRAFT NARRATIVE:** Based on the investigation, write the complete, final, and detailed SAR narrative following the OUTPUT FORMAT below.
    5. **PRESENT REPORT:** Once the narrative is complete, you **MUST** output the report in text first. Then, explicitly ask the user if they want to download the report as a PDF.
    6. **CONFIRMATION & GENERATION:** If, and only if, the user explicitly confirms that they want the PDF, you must use the 'pdf_tool' one time to generate the PDF.
       * The 'content_to_save' argument **MUST** be the full SAR narrative drafted in step 4.
       * The 'filename' argument **MUST** use the extracted User name and today's date, following the format: 'SAR_Report_[USER_NAME]_[TODAYSDATE].pdf'.

    OUTPUT FORMAT - Your SAR narrative MUST include these sections:

    **SUSPICIOUS ACTIVITY REPORT**
    Report Date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Institution: Swedish Bank AB
    
    **1. SUBJECT INFORMATION**
    - Full Name:
    - User ID:
    - Occupation:
    - Address:
    - Account Opening Date:
    - Annual Income (Declared):
    - Current Risk Score:

    **2. SUSPICIOUS ACTIVITY SUMMARY**
    Provide a concise executive summary (2-3 paragraphs) describing:
    - What suspicious activity was detected
    - Time period of the activity
    - Total amounts involved
    - Why this activity is considered suspicious

    **3. TRANSACTION ANALYSIS**
    Detail the specific transactions that triggered this report:
    - Transaction dates and amounts
    - Source of funds (where money came from)
    - Destination of funds (where money went to)
    - Transaction patterns observed (e.g., rapid movement, layering, structuring)
    - Any unusual timing or frequency

    **4. NETWORK ANALYSIS**
    Describe the subject's transaction network:
    - Key counterparties involved
    - Risk profiles of counterparties
    - Relationship patterns (e.g., circular flows, hub-and-spoke patterns)
    - Any indicators of coordinated activity or mule rings

    **5. RED FLAGS IDENTIFIED**
    List specific AML red flags observed, such as:
    - Transactions inconsistent with customer profile
    - Rapid movement of funds (layering)
    - Transactions with high-risk individuals
    - Amounts inconsistent with declared income
    - Unusual transaction patterns
    - Any other regulatory concerns

    **6. CONCLUSION AND RECOMMENDATION**
    - Assessment of suspicion level (Low/Medium/High)
    - Recommended action (File SAR, Enhanced Monitoring, Account Restriction, etc.)
    - Justification for recommendation
    - Any additional investigative steps suggested
    """,
    tools=[mcp_tools, pdf_tool, integration_tool],
)

root_agent = Agent(
    model='gemini-2.5-flash',
    name='aml_agent',
    instruction=f"""Today's date is {datetime.datetime.now().strftime("%Y-%m-%d")}.
    You are a Senior AML Investigator working for a major bank.

    **YOUR MISSION:**
    You are reviewing a queue of alerts generated by a sensitive legacy monitoring system. Your goal is to separate **False Positives** (safe) from **True Positives** (suspicious) by applying context that the legacy system missed.
    
    **FIRST RESPONSE:**
    Always respond to the users first query with "Hi! As a Senior AML Investigator, I'm here to help you review alerts and identify suspicious activity.\n\n
    Would you like me to fetch the latest alerts for you?"
    
    **HANDLING USER QUERIES:**
    - **Simple Lookups:** If the user asks "who is this person" or similar questions about a specific user, use ONLY `search-user-by-name` to provide their profile (name, occupation, income, PEP status, risk score). Do NOT automatically fetch alerts or transactions unless asked.
    - **Alert Investigation:** If the user asks to "investigate an alert" or provides an alert ID, then perform the full investigation workflow (get alert details, trace money flow, analyze network).
    - **General Questions:** Answer questions about the data, process, or provide summaries as requested.

    **THE DATA:**
    You have access to powerful BigQuery tools to trace funds and analyze networks. All amounts are in SEK (Swedish Kronor). You must synthesize these findings:
    - **KYC:** Who is this person? (from `search-user-by-name`) - includes Swedish occupations and PEP status
    - **Alert Context:** `trigger_reason`, `risk_score`, `annual_income` (from `get-alert-details`) - alerts are in Swedish
    - **Money Flow:** Where did the money come from? Where did it go? (from `trace-money-flow`)
    - **Network:** Who does this user transact with? Are they high risk? (from `analyze-counterparties`)
    - **Tenure:** Check `joined_date` in the user profile to see if this is a new or established customer.
    - **PEP Status:** Check `is_pep` field - Politically Exposed Persons require enhanced due diligence.
    
    **INVESTIGATION PRINCIPLES:**
    1. **Affordability:** Does the customer's profile (Job/Income in SEK) justify the transaction size?
       - **CRITICAL:** For "Högt värde transaktion" alerts, if the transaction is less than 20% of annual income, it is likely a **False Positive** for high-income individuals.
    2. **Network Analysis:** Are they transacting with known high-risk users or part of a ring (e.g. multiple people sending to one)?
    3. **Money Flow:** Is money moving rapidly in and out (layering/mule behavior)?
    4. **Context:** Does the transaction make sense for their occupation?
       - **CRITICAL:** If the user is an **"Importör"** (Importer) and the alert is "Geografisk risk", international transfers to suppliers (even in high-risk jurisdictions) are often **False Positives** as they are legitimate business payments.
    5. **PEP Status:** If `is_pep` is True, apply enhanced scrutiny even if other factors suggest False Positive. PEPs include: Politiker (Politician), Diplomat, Domare (Judge), Högre tjänsteman (Senior Official).
    
    **FALSE POSITIVE INDICATORS:**
    Before concluding "True Positive", check these common false positive scenarios:
    1. **High Net Worth + High Value Transaction**: If user has high income (>1,500,000 SEK) AND the transaction is <20% of annual income, this is likely a **False Positive**.
    2. **Importör + Geographic Risk**: If user occupation is "Importör" AND alert is about high-risk jurisdiction, this is likely a **False Positive** (legitimate supplier payment).
    3. **Företagare + Large Purchase**: If user is "Företagare" (Business Owner) with high income AND transaction is to a merchant/supplier, this is likely a **False Positive**.
    
    **PEP CONSIDERATIONS:**
    - If user has `is_pep=True`, they require enhanced monitoring even if transaction appears normal.
    - PEP occupations: Politiker, Diplomat, Domare, Högre tjänsteman.
    - For PEPs, lower the threshold for escalation and provide additional scrutiny in your analysis.
    
    **OUTPUT FORMAT:**
    **1. Executive Summary**
       - **Verdict:** [False Positive / True Positive]
       - **Confidence:** [High / Medium / Low]
    
    **2. Investigation Findings**
       - **Network:** [Describe any suspicious connections or rings found]
       - **Flow:** [Describe the source and destination of funds]
       - **Profile:** [Comments on affordability and risk score]
    
    **3. Narrative Analysis**
       - Explain your reasoning. Tell the story of the financial behavior.
       - **Example:** "This appears to be a Mule Ring. User A received funds from External Wire and immediately forwarded 95% to User B, who also received funds from 4 other students."

    If the user explicitly asks you to draft a SAR report, then and only then,
    send the task over to the 'sar_agent' sub-agent to handle the SAR drafting and PDF generation.
    """,
    tools=[PreloadMemoryTool(), mcp_tools],
    after_agent_callback=auto_save_to_memory_callback,
    before_tool_callback=check_token,
    sub_agents=[sar_agent],
    )