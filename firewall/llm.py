# ============================================================
# firewall/llm.py — Centralized LLM client
#
# Priority order:
# 1. Bifrost gateway (http://localhost:8080/v1) — production grade, full observability
# 2. Google Gemini direct (GOOGLE_API_KEY / GEMINI_API_KEY)
# 3. OpenAI direct (OPENAI_API_KEY)
# 4. Offline fallback mock (no API calls)
# ============================================================

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BIFROST_URL = os.getenv("BIFROST_URL", "http://localhost:8080/v1")
BIFROST_MODEL = os.getenv("BIFROST_MODEL", "gemini/gemini-flash-latest")


def get_llm_config() -> tuple:
    """
    Detect available LLM backend and return (client, model_name, backend_name).

    Returns:
        (client, model, backend)  where backend is one of:
        "bifrost" | "gemini" | "openai" | "mock"
    """
    # 1. Try Bifrost (local gateway) — check if it's running
    try:
        import urllib.request
        urllib.request.urlopen(f"{BIFROST_URL.rstrip('/v1')}/health", timeout=1)
        client = OpenAI(
            api_key="bifrost",   # Bifrost doesn't need a key — it manages upstream keys
            base_url=BIFROST_URL,
        )
        return client, BIFROST_MODEL, "bifrost"
    except Exception:
        pass  # Bifrost not running — fall through

    # 2. Google Gemini direct
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if google_key and not google_key.startswith("your-"):
        client = OpenAI(
            api_key=google_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        return client, "gemini-3.6-flash", "gemini"

    # 3. OpenAI direct
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and not openai_key.startswith("your-"):
        return OpenAI(api_key=openai_key), "gpt-4o-mini", "openai"

    # 4. Offline mock
    return None, "mock", "mock"


def llm_chat(prompt: str, max_tokens: int = 500) -> str | None:
    """
    Convenience wrapper: send a single-turn prompt and return the response text.
    Cascades gracefully: Bifrost -> Direct Gemini -> Direct OpenAI -> None (offline fallback).
    """
    backends_to_try = []

    # Check Bifrost
    try:
        import urllib.request
        urllib.request.urlopen(f"{BIFROST_URL.rstrip('/v1')}/health", timeout=1)
        backends_to_try.append(("bifrost", OpenAI(api_key="bifrost", base_url=BIFROST_URL), BIFROST_MODEL))
    except Exception:
        pass

    # Direct Gemini
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if google_key and not google_key.startswith("your-"):
        backends_to_try.append((
            "gemini",
            OpenAI(api_key=google_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
            "gemini-3.6-flash",
        ))

    # Direct OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and not openai_key.startswith("your-"):
        backends_to_try.append(("openai", OpenAI(api_key=openai_key), "gpt-4o-mini"))

    for backend, client, model in backends_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=max_tokens,
                timeout=1.5,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content.strip()
        except Exception as e:
            # Bifrost or direct model failed, try next in chain
            continue

    return None
