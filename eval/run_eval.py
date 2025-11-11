import os
import pytest
from dotenv import find_dotenv, load_dotenv
from google.adk.evaluation.agent_evaluator import AgentEvaluator

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session", autouse=True)
def load_env():
    load_dotenv(find_dotenv(".env"))


@pytest.mark.asyncio
async def test_eval_simple():
    """Test the agent's basic ability via a session file."""
    await AgentEvaluator.evaluate(
        "agent",
        os.path.join(os.path.dirname(__file__), "eval_data/evalset_nr1.evalset.json"),
        num_runs=1,
        print_detailed_results=True,
    )