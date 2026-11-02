"""Local Ollama client configuration, loaded only for real model requests."""

import math
import os


def create_chat():
    """Create a chat callable with an explicit host and finite HTTP timeout.

    Settings are process environment variables; no .env file is loaded.
    The import remains lazy so data-only unit tests do not require the SDK.
    """
    from ollama import Client

    timeout = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120"))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be positive and finite")
    client = Client(
        host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        timeout=timeout,
    )
    return client.chat
