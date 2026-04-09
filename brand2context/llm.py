"""MiniMax LLM API client."""
import json
import time
import requests
from .config import MINIMAX_API_KEY, MINIMAX_MODEL, MINIMAX_ENDPOINT
from .json_repair import repair_json

MAX_RETRIES = 5
RETRY_DELAY = 3  # seconds base


def _is_transient_error(data: dict) -> bool:
    """Check if the API error is transient and worth retrying."""
    # Standard format: base_resp.status_code
    base_resp = data.get("base_resp", {})
    status_code = base_resp.get("status_code", -1)
    status_msg = str(base_resp.get("status_msg", ""))

    if status_code in (1000, 0) or "520" in status_msg:
        return True

    # New error format: type: "error", error.type: "overloaded_error"
    error = data.get("error", {})
    error_type = error.get("type", "")
    error_msg = error.get("message", "")
    http_code = str(error.get("http_code", ""))

    if error_type == "overloaded_error" or http_code == "529":
        return True
    if "overloaded" in error_msg.lower() or "负载" in error_msg:
        return True
    if "rate_limit" in error_type or "too_many_requests" in error_type:
        return True

    return False


def _get_error_message(data: dict) -> str:
    """Extract error message from various API response formats."""
    # Standard format
    base_msg = data.get("base_resp", {}).get("status_msg", "")
    if base_msg:
        return base_msg
    # New error format
    error = data.get("error", {})
    if error.get("message"):
        return error["message"]
    return "unknown error"


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

            # Handle HTTP-level rate limiting / overloaded
            if resp.status_code in (429, 529):
                last_err = ValueError(f"LLM API rate limited (HTTP {resp.status_code})")
                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAY * (3 ** (attempt - 1))
                    wait = min(wait, 90)
                    print(f"   ⚠️ HTTP {resp.status_code} — retry {attempt}/{MAX_RETRIES} in {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()

            resp.raise_for_status()
            data = _parse_response_body(resp)

            if not data.get("choices"):
                error_msg = _get_error_message(data)
                print(f"   ⚠️ LLM API 响应异常: {json.dumps(data, ensure_ascii=False)[:500]}")

                if _is_transient_error(data):
                    last_err = ValueError(f"LLM API returned no choices: {error_msg}")
                    if attempt < MAX_RETRIES:
                        # Exponential backoff: 3s, 9s, 27s, 81s for overloaded errors
                        wait = RETRY_DELAY * (3 ** (attempt - 1)) if "overloaded" in str(data).lower() or "529" in str(data) else RETRY_DELAY * attempt
                        wait = min(wait, 90)  # cap at 90s
                        print(f"   🔄 Retry {attempt}/{MAX_RETRIES} in {wait}s (transient error)...")
                        time.sleep(wait)
                        continue
                raise ValueError(f"LLM API returned no choices: {error_msg}")

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
