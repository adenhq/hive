import re
from typing import Any

SENSITIVE_PATTERNS = {
    "api_key": re.compile(r"(sk-[a-zA-Z0-9]{32,}|AIza[a-zA-Z0-9_-]{35})"),
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "generic_secret": re.compile(r"(password|secret|token|auth|key)[\s:\"]+([a-zA-Z0-9_-]{8,})", re.IGNORECASE)
}

def mask_sensitive_data(data: Any) -> Any:
    """
    Recursively masks sensitive data in dictionaries, lists, and strings.
    """
    if isinstance(data, dict):
        return {
            k: mask_sensitive_data(v) if k not in ["api_key", "password", "token", "secret"] 
            else "********" 
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    elif isinstance(data, str):
        masked_str = data
        for label, pattern in SENSITIVE_PATTERNS.items():
            masked_str = pattern.sub(f"[MASKED_{label.upper()}]", masked_str)
        return masked_str
    return data
