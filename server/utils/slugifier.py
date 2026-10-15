"""
CARspective — Slugifier Utility
Deterministic normalization and slugification for strings.
"""

import re
import unicodedata

def slugify(text: str) -> str:
    """Deterministic, invariant slugifier."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', str(text))
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    cleaned = ascii_text.lower()
    cleaned = re.sub(r'[^a-z0-9]+', '-', cleaned)
    cleaned = re.sub(r'-+', '-', cleaned)
    return cleaned.strip('-')
