"""한자 → 한글 변환. `hanja` 라이브러리의 substitution 모드 사용."""
from __future__ import annotations

import hanja


def to_hangul(text: str) -> tuple[str, bool]:
    """한자를 한글로 치환. (변환된 텍스트, 변경 여부) 반환."""
    converted = hanja.translate(text, "substitution")
    return converted, converted != text
