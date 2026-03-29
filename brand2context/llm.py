"""MiniMax LLM API client."""
import json
import requests
from .config import MINIMAX_API_KEY, MINIMAX_MODEL, MINIMAX_ENDPOINT


def chat(prompt: str, system: str = "", max_tokens: int = 16000, temperature: float = 0.1) -> str:
    """Call MiniMax chat API and return the text response."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        MINIMAX_ENDPOINT,
        headers={
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MINIMAX_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def chat_json(prompt: str, system: str = "", max_tokens: int = 16000) -> dict:
    """Call LLM and parse JSON from the response."""
    text = chat(prompt, system, max_tokens)
    # Extract JSON from markdown code blocks if present
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())
