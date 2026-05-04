"""단락 종류 판별. 텍스트 부호와 단락 서식을 종합 판단."""
from __future__ import annotations

import re

from docx.enum.text import WD_ALIGN_PARAGRAPH

from format_spec import PREFIX_TO_KIND


SECTION_RE = re.compile(r"^\s*\d+\.\s")
END_MARK_RE = re.compile(r"^\s*-\s*이\s*상\s*-\s*$")
ATTACH_RE = re.compile(r"^\s*별\s*첨\s*\d*\s*$")
DATE_RE = re.compile(r"\d{1,4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}")
LEADING_PREFIX_RE = re.compile(r"^\s*([□\-·▷])(\s|$)")


def _looks_like_title(paragraph) -> bool:
    """center + bold/underline + 18pt 이상 run이 있으면 제목으로 간주."""
    if paragraph.alignment != WD_ALIGN_PARAGRAPH.CENTER:
        return False
    text_runs = [r for r in paragraph.runs if r.text.strip()]
    if not text_runs:
        return False
    has_emphasis = any((r.bold or r.underline) for r in text_runs)
    has_large = any(r.font.size and r.font.size.pt >= 18 for r in text_runs)
    return has_emphasis and has_large


def classify(paragraph, *, prev_kind: str | None = None,
             saw_attachment: bool = False, is_in_table: bool = False) -> str:
    """단락 종류 추정. paragraph 객체에서 정렬·서식까지 본다."""
    text = paragraph.text
    stripped = text.strip()

    if is_in_table:
        return "table_cell"

    if not stripped:
        # 빈 줄은 직전 종류 유지 (혹은 sentence)
        return prev_kind or "sentence"

    if END_MARK_RE.match(stripped):
        return "end_mark"
    if ATTACH_RE.match(stripped):
        return "attachment"

    if _looks_like_title(paragraph):
        return "attach_title" if saw_attachment else "title"

    if SECTION_RE.match(stripped):
        return "section"
    if DATE_RE.search(stripped) and len(stripped) < 30:
        return "date"

    m = LEADING_PREFIX_RE.match(text)
    if m:
        return PREFIX_TO_KIND[m.group(1)]

    # 부호 없이 공백으로 시작하면 이어진 줄로 본다
    if text.startswith((" ", "\t", "　")) and prev_kind in {
        "sentence", "dash", "middot", "triangle", "continued", "continued_2"
    }:
        return "continued"

    return prev_kind or "sentence"
