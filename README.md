# AML Agent

An AI-powered assistant for Anti-Money Laundering (AML) analysts, built with the Google Agent Development Kit (ADK). This agent streamlines investigation and reporting of suspicious financial activities.

## Features

- 🔍 **Investigation Tools**: Query user profiles, transactions, and risk scores from BigQuery
- 📊 **Alert Triage**: View and prioritize high-severity alerts
- 🕸️ **Money Flow Tracing**: Track funds across multiple hops to identify mule rings
- 📝 **SAR Generation**: Draft and export Suspicious Activity Reports as PDF
- 🧠 **Memory Bank**: Persistent memory across sessions (when deployed to Agent Engine)
- 🤝 **A2A Support**: Integrated Agent-to-Agent (A2A) protocol for discovery and cross-agent communication

---

## Prerequisites

- Python 3.11+
- Google Cloud project with Vertex AI API enabled
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed
- [ADK](https://google.github.io/adk-docs/) installed (`pip install google-adk`)

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Lormyn/aml-agent-adk.git
cd aml-agent-adk
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r agent/requirements.txt
```

### 3. Authenticate to Google Cloud

```bash
gcloud auth application-default login
```

### 4. Configure environment variables

Create a `.env` file in the `agent/` directory:

```bash
cp agent/.env.example agent/.env
```

Edit `agent/.env` with your values (see [Environment Variables](#environment-variables) below).

### 5. Run the agent locally

```bash
adk web
```

Open http://localhost:8000 in your browser.

---

## Environment Variables

Create `agent/.env` with the following variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Set to `1` to use Vertex AI | ✅ |
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID | ✅ |
| `GOOGLE_CLOUD_LOCATION` | GCP region (e.g., `us-central1`) | ✅ |
| `GOOGLE_CLOUD_STAGING_BUCKET` | GCS bucket for deployments (e.g., `gs://my-bucket`) | For deployment |
| `MCP_URL` | URL of your MCP Toolbox Cloud Run service | ✅ |
| `AGENT_ENGINE_ID` | Agent Engine ID (after first deployment) | For Memory Bank |
| `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY` | Enable telemetry (`true`/`false`) | Optional |

### Example `.env`

```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=my-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_CLOUD_STAGING_BUCKET=gs://my-staging-bucket

MCP_URL=https://toolbox-123456789.us-central1.run.app/mcp

# Set after first deployment to Agent Engine
AGENT_ENGINE_ID=1234567890123456789

GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true
```

---

## BigQuery Dataset Setup

The agent queries data from BigQuery. Sample datasets are provided in the `data/` folder.

### Included Files

| File | Description |
|------|-------------|
| `users.csv` | User profiles with KYC data, risk scores, PEP status |
| `transactions.csv` | Transaction history between users |
| `alerts.csv` | AML alerts with severity levels |
| `schema.sql` | BigQuery table schemas |
| `generate_data.py` | Script to generate synthetic data |

### Option 1: Upload Existing CSVs (Recommended)

The CSV files are ready to upload directly to BigQuery:

1. Create a dataset in BigQuery:
   ```bash
   bq mk --dataset YOUR_PROJECT:aml_dataset
   ```

2. Load each CSV file:
   ```bash
   bq load --source_format=CSV --autodetect \
     aml_dataset.users data/users.csv

   bq load --source_format=CSV --autodetect \
     aml_dataset.transactions data/transactions.csv

   bq load --source_format=CSV --autodetect \
     aml_dataset.alerts data/alerts.csv
   ```

Or upload via the [BigQuery Console](https://console.cloud.google.com/bigquery) UI.

### Option 2: Generate New Data

To generate fresh synthetic data with custom parameters:

```bash
cd data
python generate_data.py
```

This creates new CSV files that you can then upload to BigQuery.

---

## MCP Toolbox Setup

The agent requires an MCP Toolbox deployed to Cloud Run that connects to your BigQuery dataset.

### 1. Configure `mcp_server/tools.yaml`

Update the BigQuery source configuration:

```yaml
sources:
  aml-analysis-data:
    kind: bigquery
    project: ${GOOGLE_CLOUD_PROJECT}
    location: US
    useClientOAuth: false  # Use service account auth
```

### 2. Create a secret for tools.yaml

```bash
gcloud secrets create tools --data-file=mcp_server/tools.yaml
```

Or update an existing secret:

```bash
gcloud secrets versions add tools --data-file=mcp_server/tools.yaml
```

### 3. Deploy the Toolbox to Cloud Run in us-central1

```bash
export IMAGE=us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest

gcloud run deploy toolbox \
   --image $IMAGE \
   --service-account toolbox-identity \
   --region us-central1 \
   --set-secrets "/mcp_server/tools.yaml=tools:latest" \
   --args="--tools-file=/mcp_server/tools.yaml","--address=0.0.0.0","--port=8080"
```

### 4. Required IAM permissions for Service Account

The `toolbox-identity` service account needs:

```bash
# BigQuery access
gcloud projects add-iam-policy-binding YOUR_PROJECT \
  --member="serviceAccount:toolbox-identity@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding YOUR_PROJECT \
  --member="serviceAccount:toolbox-identity@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"

# Secret access
gcloud secrets add-iam-policy-binding tools \
  --member="serviceAccount:toolbox-identity@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Deployment to Agent Engine

### First-time deployment

```bash
adk deploy agent_engine \
  --staging_bucket=gs://YOUR_STAGING_BUCKET \
  --display_name=aml_agent \
  agent
```

**Save the returned Agent Engine ID** and add it to your `.env`:
```
AGENT_ENGINE_ID=1234567890123456789
```

### Update existing deployment

```bash
adk deploy agent_engine \
  --staging_bucket=gs://YOUR_STAGING_BUCKET \
  --agent_engine_id="projects/PROJECT_ID/locations/LOCATION/reasoningEngines/ENGINE_ID" \
  agent
```

### Grant Agent Engine access to MCP Toolbox

```bash
gcloud run services add-iam-policy-binding toolbox \
  --member="serviceAccount:service-PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=us-central1
```

---

## A2A Protocol (Agent-to-Agent)

The AML Agent supports the [A2A protocol](https://a2aprotocol.org/), allowing it to be discovered and called by other agents.

### 1. Start the A2A Server

Exposes the agent card and JSON-RPC endpoint on port 9999.

```bash
python -m agent.a2a.server
```

Verified at: `http://localhost:9999/.well-known/agent.json`

### 2. Test with Hello Client

A sample client that discovers the AML agent and sends an investigation request.

```bash
python -m agent.a2a.hello_client
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Engine                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     root_agent                          │    │
│  │                (Gemini 3 Flash Preview)                  │    │
│  │  • Investigates alerts                                   │    │
│  │  • Queries user profiles                                 │    │
│  │  • Traces money flows                                    │    │
│  └──────────────────────┬─────────────┬─────────────────────┘    │
│                         │             │                          │
│                         │ delegates   │ A2A Bridge               │
│  ┌──────────────────────▼───────┐    ┌▼─────────────────────────┐│
│  │           sar_agent          │    │      A2A Executor        ││
│  │  • Drafts SAR reports        │    │  (agent/a2a/executor.py) ││
│  │  • Generates PDF files       │    └┬─────────────────────────┘│
│  └──────────────────────────────┘     │                          │
└────────────────────────────┬───────────┼────────────────────────┘
                             │           │
                             ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Toolbox (Cloud Run)                       │
│  • get-high-priority-alerts                                      │
│  • get-user-details                                              │
│  • trace-money-flow                                              │
│  • analyze-counterparties                                        │
│  • get-recent-transactions                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BigQuery                                 │
│  • aml_dataset.users                                             │
│  • aml_dataset.transactions                                      │
│  • aml_dataset.alerts                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Usage Examples

**Investigate an alert:**
> "Show me the high priority alerts"

**Look up a user:**
> "Get me details on user U-SE-001"

**Trace money flow:**
> "Trace the money flow from user U-SE-001"

**Generate a SAR:**
> "Draft a SAR report for alert ID abc-123"

---

## Troubleshooting

### 401 Unauthorized errors
- Ensure `gcloud auth application-default login` is completed
- Check that `useClientOAuth: false` in `mcp_server/tools.yaml`

### 403 Forbidden errors
- Verify IAM permissions for the Toolbox service account
- Check Cloud Run invoker permissions for Agent Engine

### 500 Internal Server errors
- Add `bigquery.jobUser` role to the Toolbox service account
- Check Cloud Run logs for detailed error messages

---

## License

Apache 2.0
