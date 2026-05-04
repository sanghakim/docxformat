"""단락 종류 판별. 시작 부호와 위치(첫/끝)로 분류한다."""
from __future__ import annotations

import re

from format_spec import PREFIX_TO_KIND


SECTION_RE = re.compile(r"^\s*\d+\.\s")
END_MARK_RE = re.compile(r"^\s*-\s*이\s*상\s*-\s*$")
ATTACH_RE = re.compile(r"^\s*별\s*첨\s*\d*\s*$")
DATE_RE = re.compile(r"\d{1,4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}")


def classify(text: str, *, is_first: bool = False, is_in_table: bool = False) -> str:
    """단락 텍스트에서 종류를 추정. 모르면 'sentence'로 폴백."""
    stripped = text.strip()
    if not stripped:
        return "sentence"

    if is_in_table:
        return "table_cell"

    if END_MARK_RE.match(stripped):
        return "end_mark"
    if ATTACH_RE.match(stripped):
        return "attachment"
    if SECTION_RE.match(stripped):
        return "section"
    if DATE_RE.search(stripped) and len(stripped) < 30:
        return "date"

    first_char = stripped[0]
    if first_char in PREFIX_TO_KIND:
        # "- 이 상 -"는 위에서 걸러짐
        return PREFIX_TO_KIND[first_char]

    # 본문 첫 단락이고 부호도 없으면 제목으로 가정
    if is_first:
        return "title"

    return "sentence"
