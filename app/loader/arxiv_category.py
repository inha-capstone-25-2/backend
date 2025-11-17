from __future__ import annotations

def parse_categories(raw: str | None) -> list[str]:
    """
    공백 구분 문자열 -> 코드 배열.
    예: "math.NT math.AG" -> ["math.NT", "math.AG"]
    """
    if not raw:
        return []
    return [c.strip() for c in raw.split() if c.strip()]