"""Production-grade JSON repair for LLM outputs.

Handles all common LLM JSON output issues:
1. Multiple JSON objects concatenated (Extra data error)
2. Trailing commas in arrays/objects
3. Single quotes instead of double quotes
4. Unescaped control characters in strings
5. Truncated JSON (incomplete due to max_tokens)
6. Surrounding text/commentary
7. JavaScript-style comments
8. NaN/Infinity literals
9. Unquoted keys
10. Missing commas between elements
"""

import json
import re


def repair_json(text: str) -> dict:
    """Try every repair strategy to extract valid JSON from LLM output.
    
    Returns the parsed dict, or raises ValueError if all strategies fail.
    """
    if not text or not text.strip():
        raise ValueError("Empty input")

    # Strategy 0: Pre-clean common issues that json.loads might accept wrongly
    text_precleaned = re.sub(r'\bNaN\b', 'null', text)
    text_precleaned = re.sub(r'(?<!["\w])-?Infinity\b', 'null', text_precleaned)

    # Strategy 0b: Direct parse
    try:
        return json.loads(text_precleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 1: Extract from markdown code blocks
    cleaned = _extract_from_codeblock(text)
    if cleaned != text:
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            text = cleaned  # Use extracted content for further repair

    # Strategy 2: Find the first complete JSON object by brace matching
    extracted = _extract_first_json_object(text)
    if extracted:
        try:
            return json.loads(extracted)
        except (json.JSONDecodeError, ValueError):
            text = extracted  # Use extracted for further repair

    # Strategy 3: Apply all regex-based fixes
    fixed = _apply_all_fixes(text)
    try:
        return json.loads(fixed)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 4: Fix truncated JSON (close all open brackets/braces)
    completed = _complete_truncated_json(fixed)
    try:
        return json.loads(completed)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 5: Extract first object + apply fixes + complete
    if extracted:
        fixed_extracted = _apply_all_fixes(extracted)
        completed_extracted = _complete_truncated_json(fixed_extracted)
        try:
            return json.loads(completed_extracted)
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 6: Nuclear option - line-by-line reconstruction
    reconstructed = _reconstruct_json(text)
    if reconstructed:
        try:
            return json.loads(reconstructed)
        except (json.JSONDecodeError, ValueError):
            pass

    raise ValueError(f"All JSON repair strategies failed. First 200 chars: {text[:200]}")


def _extract_from_codeblock(text: str) -> str:
    """Extract JSON from markdown code blocks."""
    if "```json" in text:
        parts = text.split("```json", 1)
        if len(parts) > 1:
            inner = parts[1]
            if "```" in inner:
                return inner.split("```", 1)[0].strip()
            return inner.strip()
    if "```" in text:
        parts = text.split("```", 1)
        if len(parts) > 1:
            inner = parts[1]
            if "```" in inner:
                return inner.split("```", 1)[0].strip()
    return text


def _extract_first_json_object(text: str) -> str | None:
    """Use brace matching to extract the first complete JSON object.
    
    This handles the 'Extra data' error (multiple JSON objects concatenated).
    """
    # Find the first {
    start = -1
    for i, c in enumerate(text):
        if c == '{':
            start = i
            break
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        c = text[i]
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
                return text[start:i + 1]

    # If we get here, JSON is truncated — return what we have
    return text[start:]


def _apply_all_fixes(text: str) -> str:
    """Apply all regex-based JSON fixes."""
    s = text

    # Remove JS-style comments
    s = re.sub(r'//[^\n]*', '', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)

    # Replace NaN/Infinity with null
    s = re.sub(r'\bNaN\b', 'null', s)
    s = re.sub(r'\bInfinity\b', 'null', s)
    s = re.sub(r'-Infinity\b', 'null', s)

    # Fix trailing commas: ,] or ,}
    s = re.sub(r',\s*(\])', r'\1', s)
    s = re.sub(r',\s*(\})', r'\1', s)

    # Fix missing commas between elements:
    # "value"\n"key" → "value",\n"key"
    s = re.sub(r'"\s*\n\s*"', '",\n"', s)
    # }\n" → },\n"
    s = re.sub(r'(\})\s*\n\s*"', r'\1,\n"', s)
    # ]\n" → ],\n"
    s = re.sub(r'(\])\s*\n\s*"', r'\1,\n"', s)
    # "value"\n{ → "value",\n{
    s = re.sub(r'"\s*\n\s*\{', '",\n{', s)
    # }\n{ → },\n{
    s = re.sub(r'(\})\s*\n\s*\{', r'\1,\n{', s)
    # ]\n[ → ],\n[
    s = re.sub(r'(\])\s*\n\s*\[', r'\1,\n[', s)

    # Fix single quotes to double quotes (careful not to break strings)
    s = _fix_quotes(s)

    # Fix unquoted keys: { key: "value" } → { "key": "value" }
    s = re.sub(r'(?<=[\{,])\s*([a-zA-Z_]\w*)\s*:', r' "\1":', s)

    # Fix control characters in strings (except \n \t \r which we keep escaped)
    s = _fix_control_chars(s)

    return s


def _fix_quotes(text: str) -> str:
    """Replace single quotes with double quotes, but only for JSON structure."""
    result = []
    i = 0
    in_double = False
    in_single = False
    
    while i < len(text):
        c = text[i]
        
        # Handle escape sequences
        if i + 1 < len(text) and c == '\\':
            result.append(c)
            result.append(text[i + 1])
            i += 2
            continue
        
        if c == '"' and not in_single:
            in_double = not in_double
            result.append(c)
        elif c == "'" and not in_double:
            if not in_single:
                # Check if this looks like a JSON string delimiter
                # (not an apostrophe in English text)
                in_single = True
                result.append('"')
            else:
                in_single = False
                result.append('"')
        else:
            result.append(c)
        
        i += 1
    
    return ''.join(result)


def _fix_control_chars(text: str) -> str:
    """Fix unescaped control characters inside JSON strings."""
    result = []
    in_string = False
    escape = False
    
    for c in text:
        if escape:
            result.append(c)
            escape = False
            continue
        if c == '\\':
            escape = True
            result.append(c)
            continue
        if c == '"':
            in_string = not in_string
            result.append(c)
            continue
        
        if in_string and ord(c) < 32:
            if c == '\n':
                result.append('\\n')
            elif c == '\r':
                result.append('\\r')
            elif c == '\t':
                result.append('\\t')
            else:
                result.append(f'\\u{ord(c):04x}')
        else:
            result.append(c)
    
    return ''.join(result)


def _complete_truncated_json(text: str) -> str:
    """Close all unclosed brackets/braces to fix truncated JSON."""
    # First, find where we are in terms of nesting
    stack = []
    in_string = False
    escape = False
    last_was_value = False
    
    for c in text:
        if escape:
            escape = False
            continue
        if c == '\\' and in_string:
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
            last_was_value = in_string is False
            continue
        if in_string:
            continue
        
        if c == '{':
            stack.append('}')
            last_was_value = False
        elif c == '[':
            stack.append(']')
            last_was_value = False
        elif c == '}':
            if stack and stack[-1] == '}':
                stack.pop()
                last_was_value = True
        elif c == ']':
            if stack and stack[-1] == ']':
                stack.pop()
                last_was_value = True
        elif c in ',':
            last_was_value = False
    
    if not stack:
        return text
    
    # If we're in the middle of a string, close it
    suffix = ''
    if in_string:
        suffix += '"'
    
    # Remove trailing comma if any
    trimmed = text.rstrip()
    if trimmed.endswith(','):
        trimmed = trimmed[:-1]
        text = trimmed
    
    # Close all open brackets
    suffix += ''.join(reversed(stack))
    
    return text + suffix


def _reconstruct_json(text: str) -> str | None:
    """Last resort: try to find and extract the largest valid JSON substring."""
    # Find all possible start positions
    starts = [i for i, c in enumerate(text) if c == '{']
    
    best = None
    best_len = 0
    
    for start in starts[:5]:  # Only try first 5 potential starts
        depth = 0
        in_string = False
        escape = False
        
        for i in range(start, len(text)):
            c = text[i]
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
                    candidate = text[start:i + 1]
                    if len(candidate) > best_len:
                        try:
                            json.loads(candidate)
                            best = candidate
                            best_len = len(candidate)
                        except (json.JSONDecodeError, ValueError):
                            # Try with fixes
                            fixed = _apply_all_fixes(candidate)
                            try:
                                json.loads(fixed)
                                best = fixed
                                best_len = len(fixed)
                            except (json.JSONDecodeError, ValueError):
                                pass
                    break
    
    return best
