from llm_clients.gemini_client import run_prompt as gemini
from llm_clients.claude_client import run_prompt as claude

def run_agent(prompt: str, model="claude") -> str:
    if model == "gemini":
        return gemini(prompt)
    return claude(prompt)

