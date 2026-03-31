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
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    
    # 调试：如果 choices 为空，打印完整响应
    if not data.get("choices"):
        print(f"   ⚠️ LLM API 响应异常: {json.dumps(data, ensure_ascii=False)[:500]}")
        raise ValueError(f"LLM API returned no choices: {data.get('base_resp', {}).get('status_msg', 'unknown error')}")
    
    return data["choices"][0]["message"]["content"]


def chat_json(prompt: str, system: str = "", max_tokens: int = 16000) -> dict:
    """Call LLM and parse JSON from the response."""
    text = chat(prompt, system, max_tokens)
    # Extract JSON from markdown code blocks if present
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    
    text = text.strip()
    
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试修复常见 JSON 问题
    import re
    # 修复尾随逗号
    fixed = re.sub(r',\s*([}\]])', r'\1', text)
    # 修复缺少逗号（行尾的 " 后面紧跟换行和 "）
    fixed = re.sub(r'"\s*\n\s*"', '",\n"', fixed)
    # 修复缺少逗号（} 或 ] 后面紧跟换行和 "）
    fixed = re.sub(r'([}\]])\s*\n\s*"', r'\1,\n"', fixed)
    
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON 修复失败，原始错误: {e}")
        print(f"   ⚠️ 原始文本前500字符: {text[:500]}")
        raise
