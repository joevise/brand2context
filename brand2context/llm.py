"""MiniMax LLM API client."""
import json
import time
import requests
from .config import MINIMAX_API_KEY, MINIMAX_MODEL, MINIMAX_ENDPOINT
from .json_repair import repair_json

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def _parse_response_body(resp) -> dict:
    """Parse response body, handling non-standard multi-line JSON from MiniMax."""
    raw = resp.text.strip()
    # Normal case: single JSON object
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # MiniMax sometimes returns multiple JSON objects concatenated (e.g. SSE leak).
    # Take only the first complete JSON object.
    for end in range(len(raw), 0, -1):
        try:
            return json.loads(raw[:end])
        except json.JSONDecodeError:
            continue
    # Last resort: try line-by-line
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Cannot parse MiniMax response: {raw[:300]}")


def chat(prompt: str, system: str = "", max_tokens: int = 16000, temperature: float = 0.1) -> str:
    """Call MiniMax chat API and return the text response. Retries on transient errors."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
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
                timeout=300,
            )
            resp.raise_for_status()
            data = _parse_response_body(resp)

            if not data.get("choices"):
                status_msg = data.get("base_resp", {}).get("status_msg", "unknown error")
                status_code = data.get("base_resp", {}).get("status_code", -1)
                print(f"   ⚠️ LLM API 响应异常: {json.dumps(data, ensure_ascii=False)[:500]}")
                # Retry on transient server errors (520, 1000, empty status)
                if status_code in (1000, 0) or "520" in str(status_msg):
                    last_err = ValueError(f"LLM API returned no choices: {status_msg}")
                    if attempt < MAX_RETRIES:
                        print(f"   🔄 Retry {attempt}/{MAX_RETRIES} in {RETRY_DELAY}s...")
                        time.sleep(RETRY_DELAY * attempt)
                        continue
                raise ValueError(f"LLM API returned no choices: {status_msg}")

            return data["choices"][0]["message"]["content"]

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_err = e
            if attempt < MAX_RETRIES:
                print(f"   🔄 Network error, retry {attempt}/{MAX_RETRIES} in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY * attempt)
                continue
            raise

    raise last_err


def chat_json(prompt: str, system: str = "", max_tokens: int = 16000) -> dict:
    """Call LLM and parse JSON from the response using production-grade repair."""
    text = chat(prompt, system, max_tokens)
    return repair_json(text)
