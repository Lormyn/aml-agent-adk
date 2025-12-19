"""Hello World client that demonstrates A2A communication with the AML agent.

Run with: python -m hello_client

Make sure the AML A2A server is running first:
    python -m agent.a2a_server
"""

import asyncio
import httpx


async def main():
    print("=" * 60)
    print("Hello World A2A Client")
    print("=" * 60)

    base_url = "http://localhost:9999"

    # Step 1: Discover the agent
    print("\n1. Discovering AML agent...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/.well-known/agent.json")
            response.raise_for_status()
            agent_card = response.json()
            print(f"   ✅ Found agent: {agent_card.get('name')}")
            print(f"   📝 Description: {agent_card.get('description')}")
            if agent_card.get("skills"):
                print("   🔧 Skills:")
                for skill in agent_card["skills"]:
                    print(f"      - {skill.get('name')}: {skill.get('description')}")
        except httpx.ConnectError:
            print("   ❌ Could not connect to AML agent at", base_url)
            print("   💡 Make sure to run: python -m agent.a2a_server")
            return
        except Exception as e:
            print(f"   ❌ Error discovering agent: {e}")
            return

    # Step 2: Send a test message
    print("\n2. Sending test message to AML agent...")
    test_message = "Get high priority alerts"
    print(f"   📤 Message: '{test_message}'")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/",
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [{"text": test_message}],
                            "messageId": "test-msg-1",
                        }
                    },
                },
            )
            response.raise_for_status()
            result = response.json()

            print("\n3. Response from AML agent:")
            print("-" * 40)
            if "result" in result:
                # Extract the agent's response
                task_result = result.get("result", {})
                if "result" in task_result:
                    artifacts = task_result["result"].get("artifacts", [])
                    for artifact in artifacts:
                        for part in artifact.get("parts", []):
                            if "text" in part:
                                print(part["text"])
                elif "status" in task_result:
                    print(f"Task status: {task_result['status'].get('state')}")
                    if task_result["status"].get("message"):
                        message = task_result["status"]["message"]
                        for part in message.get("parts", []):
                            if "text" in part:
                                print(part["text"])
                else:
                    print(result)
            elif "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(result)

    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
