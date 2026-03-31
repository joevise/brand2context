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
    
    # 尝试修复：用 Python ast 的宽松解析
    try:
        import re
        # 修复尾随逗号
        fixed = re.sub(r',\s*([}\]])', r'\1', text)
        # 修复缺少逗号
        fixed = re.sub(r'"\s*\n\s*"', '",\n"', fixed)
        fixed = re.sub(r'([}\]])\s*\n\s*"', r'\1,\n"', fixed)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    # 最后手段：逐字符找到有效 JSON 的结束位置，截断解析
    try:
        # 找到最后一个完整的 } 并截断
        depth = 0
        last_valid = 0
        in_string = False
        escape = False
        for i, c in enumerate(text):
            if escape:
                escape = False
                continue
            if c == '\\' and in_string:
                escape = True
                continue
            if c == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    last_valid = i + 1
                    break
        
        if last_valid > 0:
            truncated = text[:last_valid]
            return json.loads(truncated)
    except json.JSONDecodeError:
        pass
    
    # 真的没办法了，让 LLM 重试一次（简化 prompt）
    print("   ⚠️ JSON 解析全部失败，尝试让 LLM 重新生成...")
    retry_prompt = f"以下是一段损坏的 JSON，请修复并返回有效的 JSON（只返回 JSON，不要其他文字）：\n\n{text[:8000]}"
    retry_text = chat(retry_prompt, system="You are a JSON repair tool. Output ONLY valid JSON.", max_tokens=16000)
    if "```json" in retry_text:
        retry_text = retry_text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in retry_text:
        retry_text = retry_text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(retry_text.strip())
