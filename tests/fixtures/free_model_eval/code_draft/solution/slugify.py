import re


def slugify(value: str) -> str:
    """Return a lowercase ASCII-style slug for the synthetic fixture."""
    value = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", "", value)
