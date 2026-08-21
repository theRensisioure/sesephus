import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.ui import Console

async def main():
    # Configuration for local LM Studio using the new AutoGen 0.4+ API
    # Local models require model_info for token/feature detection
    client = OpenAIChatCompletionClient(
        model="local-model",
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown",
        }
    )

    # Define the Assistant Agent
    assistant = AssistantAgent(
        name="assistant",
        model_client=client,
        system_message="You are the Arcadium assistant running on an RTX 5080. Respond with 'TERMINATE' when finished.",
    )

    # In the new API, we use teams for orchestration
    team = RoundRobinGroupChat([assistant], termination_condition=None)

    # Start the conversation
    stream = team.run_stream(task="What is the current status of the RTX 5080 inference node for Arcadium?")
    await Console(stream)

if __name__ == "__main__":
    asyncio.run(main())
