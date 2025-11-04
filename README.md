# Definition

This project implements an AI-powered assistant for Anti-Money Laundering (AML) analysts at "Swedish Bank AB". The system is built using the Google Agent Development Kit (ADK) and is designed to streamline the investigation and reporting of suspicious financial activities.



# Setup

Create a `.env` file in the `aml_agent` directory to store the below variables (which you need to set). 

Keep in mind you also need to configure your MCP server and tools to read from your BigQuery dataset & tables in order for the agent to run.

```
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=

BIGQUERY_PROJECT=
BIGQUERY_LOCATION=

AGENT_ENGINE_ID="Requires having deployed your agent to Agent Engine"

OAUTH_CLIENT_ID="Requires setting up an OAuth profile in GCP"
OAUTH_CLIENT_SECRET="Requires setting up an OAuth profile in GCP"

MCP_URL="Required deploying your MCP server to Cloud Run"
```



## Agents

The system consists of two main agents:

1.  **`root_agent`**: The primary assistant for an AML analyst. It can perform initial investigations by looking up user information from a BigQuery backend.
2.  **`sar_agent`**: A specialized sub-agent responsible for drafting and generating Suspicious Activity Reports (SARs) in PDF format.

The `root_agent` is the main entry point for the analyst. Its primary responsibilities are:

*   **Initial Investigation**: It uses a set of tools to query a BigQuery dataset for user information, including risk scores, transaction data, and KYC (Know Your Customer) details.
*   **Presenting Findings**: It presents the gathered information to the analyst in a clear and concise manner.
*   **Delegation**: If the analyst decides that a SAR is warranted, the `root_agent` delegates the task of drafting the report to the `sar_agent`.

The `sar_agent` is a specialized agent focused on the creation of SARs. Its workflow is as follows:

1.  **User Identification**: It identifies the user ID for whom the SAR is being created.
2.  **Data Gathering**: It uses the available tools to gather all necessary information about the user.
3.  **Narrative Drafting**: It drafts a comprehensive SAR narrative based on the gathered data.
4.  **PDF Generation**: It can generate a PDF version of the SAR for download.




## Tools

The agents have access to a variety of tools to perform their functions. These tools are defined in `mcp_server/tools.yaml`.

These tools query the output of an AML risk model.

*   `get-user-full-report`: Retrieves all features and the final risk assessment for a specific user.
*   `get-top-n-risk-users`: Lists the top N users with the highest risk scores.
*   `find-flags-high-deposits`: Identifies users with unusually large single-day deposit volumes.
*   `new-account-international-risk`: Finds new accounts with a high number of international transfers.

These tools query the KYC (Know Your Customer) data.

*   `get-user-kyc-details`: Retrieves all available KYC details for a specific user.
*   `find-users-by-occupation`: Finds all users with a specific occupation.
*   `get-potential-pep-matches`: Retrieves a list of users flagged as Politically Exposed Persons (PEPs).
*   `find-users-by-birth-year-range`: Identifies users born within a specified year range.

Other tools:

*   **`pdf_tool`**: A custom python function that allows the `sar_agent` to generate a PDF report.
*   **`integration_tool`**: A tool for sending an email summary of the conversation. Built using Application Integration in GCP.




## Running the Agent

To interact with the agent, call ADK's web server via 

```bash
adk web 
```

Once deployed to Agent Engine, invoke via 

```bash
adk web --session_service_uri=agentengine://projects/PROJECT_ID/locations/LOCATION_ID/reasoningEngines/REASONING_ENGINE_ID
```

Leverage Agent Engine Memory Bank using 

```bash
adk web /PATH/TO/YOUR/AGENT/FOLDER --memory_service_uri="agentengine://REASONING_ENGINE_ID"
```



## Deployment

To deploy the agent to Agent Engine, use the following command:

```bash
adk deploy agent_engine --project=<YOUR_PROJECT_ID> --region=<YOUR_REGION> --staging_bucket=gs://<YOUR_STAGING_BUCKET> --adk_app=agent --display_name=<YOUR_DISPLAY_NAME> /PATH/TO/YOUR/AGENT/FOLDER
```




### Examples
Ask it to "investigate user U-HR-005" or "show me the top 5 riskiest users". 

If you want to draft a SAR, you can instruct the agent to do so, and it will delegate the task to the `sar_agent`.