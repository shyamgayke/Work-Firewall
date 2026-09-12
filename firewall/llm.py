# ============================================================
# firewall/llm.py
# Centralized LLM client initialization supporting:
# - Google Gemini (via OpenAI compatibility layer)
# - OpenAI (GPT-4o-mini)
# - Fallback offline mock (if no key is provided)
# ============================================================

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def get_llm_config():
    """
    Detect available API key and return (client, model_name).
    """
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if google_key and not google_key.startswith("your-"):
        # Google Gemini via OpenAI-compatible endpoint
        client = OpenAI(
            api_key=google_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        return client, "gemini-1.5-flash"

    if openai_key and not openai_key.startswith("your-"):
        client = OpenAI(api_key=openai_key)
        return client, "gpt-4o-mini"

    # If neither key is provided, return None to indicate fallback mock mode
    return None, "mock"
