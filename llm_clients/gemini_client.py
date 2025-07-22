import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get the API key
api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-pro")

def run_prompt(prompt, tools=None):
    response = model.generate_content(prompt)
    return response.text  # or parse tool calls if you use function calling