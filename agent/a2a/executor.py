"""A2A Executor that bridges the A2A protocol to the ADK AML agent."""

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from ..agent import root_agent


class AMLAgentExecutor(AgentExecutor):
    """Executor that bridges A2A requests to the ADK AML agent."""

    def __init__(self):
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=root_agent,
            app_name="aml_agent_a2a",
            session_service=self.session_service,
        )

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent with the given A2A request context."""
        # Extract user message from A2A context
        # A2A Part wraps content in .root (e.g., TextPart with .text)
        user_message_text = ""
        if context.message and context.message.parts:
            for part in context.message.parts:
                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                    user_message_text = part.root.text
                    break

        if not user_message_text:
            await event_queue.enqueue_event(
                new_agent_text_message("No message provided.")
            )
            return

        # Create or get session
        session_id = context.task_id or "default_session"
        session = await self.session_service.get_session(
            app_name="aml_agent_a2a",
            user_id="a2a_user",
            session_id=session_id,
        )
        if not session:
            session = await self.session_service.create_session(
                app_name="aml_agent_a2a",
                user_id="a2a_user",
                session_id=session_id,
            )

        # Create a proper Content object for ADK Runner
        user_content = Content(
            role="user",
            parts=[Part(text=user_message_text)]
        )

        # Run the agent and collect response
        response_text = ""
        async for event in self.runner.run_async(
            user_id="a2a_user",
            session_id=session.id,
            new_message=user_content,
        ):
            # Collect final response from agent
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text += part.text

        # Send response back via A2A
        if response_text:
            await event_queue.enqueue_event(new_agent_text_message(response_text))
        else:
            await event_queue.enqueue_event(
                new_agent_text_message("Agent did not produce a response.")
            )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel is not supported for this agent."""
        raise Exception("cancel not supported")

