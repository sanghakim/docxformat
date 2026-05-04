"""부호 변환: 전각/유사 글리프 → 표준 부호."""
from __future__ import annotations

from format_spec import SYMBOL_MAP


def normalize_symbols(text: str) -> tuple[str, bool]:
    """변환된 새 텍스트와 변경 여부를 반환."""
    out = text
    for src, dst in SYMBOL_MAP.items():
        out = out.replace(src, dst)
    return out, out != text
