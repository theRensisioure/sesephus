import autogen

# Configuration for local LM Studio
# Note: RTX 5080 with 16GB VRAM is ready for high-speed local inference.
config_list = [
    {
        "model": "local-model", # LM Studio allows any name
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
    }
]

# Define the Assistant Agent
# This agent will utilize the 5080's compute power via LM Studio.
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={
        "config_list": config_list,
        "temperature": 0.7,
    },
)

# Define the User Proxy Agent
# human_input_mode="NEVER" for automated testing.
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=2,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"work_dir": "coding", "use_docker": False},
)

# Start the conversation
# Testing the agent's self-awareness of its local hardware context.
user_proxy.initiate_chat(
    assistant,
    message="What is the current status of the RTX 5080 inference node for Arcadium? Respond with 'TERMINATE' when done.",
)
