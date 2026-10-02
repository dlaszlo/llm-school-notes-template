"""Remove secret values and token-like strings from anything leaving the host (plan 7.5)."""

import re

PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}"),           # OpenRouter
    re.compile(r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"),  # Anthropic / OpenAI API keys
    re.compile(r"ya29\.[A-Za-z0-9_.-]{10,}"),            # Google access token
    re.compile(r"1//[A-Za-z0-9_-]{20,}"),                # Google refresh token
    re.compile(r"GOCSPX-[A-Za-z0-9_-]{10,}"),            # Google client secret
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"),
]
MASK = "[redacted]"


def redact_text(text: str, secrets: tuple[str, ...] = ()) -> str:
    for secret in secrets:
        if secret and len(secret) >= 4:
            text = text.replace(secret, MASK)
    for pattern in PATTERNS:
        text = pattern.sub(MASK, text)
    return text


def redact(value, secrets: tuple[str, ...] = ()):
    """Redact every string in a JSON-like value (keys included)."""
    if isinstance(value, str):
        return redact_text(value, secrets)
    if isinstance(value, list):
        return [redact(v, secrets) for v in value]
    if isinstance(value, dict):
        return {redact(k, secrets): redact(v, secrets) for k, v in value.items()}
    return value
