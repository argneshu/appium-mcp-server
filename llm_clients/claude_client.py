import anthropic

client = anthropic.Anthropic(api_key="YOUR_CLAUDE_API_KEY")

def run_prompt(prompt: str) -> str:
    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1024,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

