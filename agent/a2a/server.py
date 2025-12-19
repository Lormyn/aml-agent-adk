"""A2A Server entry point for the AML agent.

Run with: python -m agent.a2a.server
"""

import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from .executor import AMLAgentExecutor


def main():
    # Define what this agent can do
    skill = AgentSkill(
        id="aml_investigation",
        name="AML Investigation",
        description=(
            "Investigate anti-money laundering alerts, analyze transaction flows, "
            "identify suspicious patterns, and classify alerts as True/False Positives."
        ),
        tags=["aml", "investigation", "compliance", "fraud"],
        examples=[
            "Get high priority alerts",
            "Investigate alert A-123",
            "Who is Erik Lindgren?",
            "Trace money flow for user U-456",
        ],
    )

    # Public agent card for discovery
    public_agent_card = AgentCard(
        name="AML Investigation Agent",
        description=(
            "A Senior AML Investigator agent that reviews alerts, traces money flows, "
            "analyzes counterparty networks, and identifies suspicious activity."
        ),
        url="http://localhost:9999/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill],
    )

    # Create request handler with our executor
    request_handler = DefaultRequestHandler(
        agent_executor=AMLAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    # Create A2A server
    server = A2AStarletteApplication(
        agent_card=public_agent_card,
        http_handler=request_handler,
    )

    print("Starting AML Agent A2A Server on http://localhost:9999")
    print("Agent card available at: http://localhost:9999/.well-known/agent.json")
    uvicorn.run(server.build(), host="0.0.0.0", port=9999)


if __name__ == "__main__":
    main()
