"""Local Ollama client configuration, loaded only for real model requests."""

import math
import os
from collections.abc import Callable


def create_chat(on_progress: Callable[[], None] | None = None,
                on_text: Callable[[str], None] | None = None):
    """Create a chat callable with an explicit host and finite HTTP timeout.

    Settings are process environment variables; no .env file is loaded.
    The import remains lazy so data-only unit tests do not require the SDK.
    """
    from ollama import Client, Message, ResponseError
    from httpx import RequestError

    timeout = float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120"))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("OLLAMA_TIMEOUT_SECONDS must be positive and finite")
    client = Client(
        host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
        timeout=timeout,
    )
    def chat(**kwargs):
        try:
            if on_progress is None and on_text is None:
                return client.chat(**kwargs)
            # Aggregate streamed tool calls exactly as the non-streaming agent
            # expects. Never send raw content/thinking to a progress callback.
            chunks = client.chat(**{**kwargs, 'stream': True})
            content, thinking, calls = [], [], []
            last = None
            for chunk in chunks:
                last = chunk
                content.append(chunk.message.content or '')
                thinking.append(chunk.message.thinking or '')
                calls.extend(chunk.message.tool_calls or [])
                if on_progress:
                    on_progress()
                # This Qwen template prefills an opening think block. Until its
                # closing delimiter is received, all content stays private.
                if on_text and not calls:
                    visible = _stream_visible_text(''.join(content))
                    if visible:
                        on_text(visible)
            if last is None:
                raise ConnectionError('The local model returned an empty stream')
            return last.model_copy(update={'message': Message(role='assistant',
                content=''.join(content), thinking=''.join(thinking), tool_calls=calls)})
        except (RequestError, ResponseError) as exc:
            raise ConnectionError("Unable to complete the local model request") from exc

    return chat


def _stream_visible_text(content: str) -> str:
    """Only reveal final text after a complete closing reasoning delimiter."""
    import re
    from .response_quality import clean_model_answer
    closings = list(re.finditer(r'</think\s*>', content, re.IGNORECASE))
    if not closings:
        return ''
    candidate = content[closings[-1].end():]
    if re.search(r'<think(?:\s|>)', candidate, re.IGNORECASE):
        return ''
    # Keep incomplete delimiters/private blocks and raw tool markup buffered.
    opening = candidate.rfind('<')
    if opening >= 0 and '>' not in candidate[opening:]:
        candidate = candidate[:opening]
    if re.search(r'<(?:tool_call|tool_response)\b', candidate, re.IGNORECASE):
        return ''
    return clean_model_answer(candidate)
