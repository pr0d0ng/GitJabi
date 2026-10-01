import os
from langchain_openai import AzureChatOpenAI


def get_azure_open_ai_instance():
    if not hasattr(get_azure_open_ai_instance, '_instance'):
        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY", "")       #type: ignore
        )
        setattr(get_azure_open_ai_instance, '_instance', llm)
    return getattr(get_azure_open_ai_instance, "_instance")

