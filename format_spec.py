"""표준 문서 포맷 스펙. 첨부 이미지의 양식을 그대로 옮긴 것.

bold/underline 필드가 None이면 '강제하지 않음' (원본 보존). True/False면 강제."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParagraphRule:
    name: str
    font_size_pt: float
    space_after_pt: float
    left_indent_chars: int = 0
    bold: bool | None = None
    underline: bool | None = None
    align: str | None = None  # "left" | "center" | "right"


# 단락 종류별 규칙. bold/underline은 title 계열만 강제.
RULES: dict[str, ParagraphRule] = {
    "title":       ParagraphRule("title",       20, 0,  bold=True, underline=True, align="center"),
    "date":        ParagraphRule("date",        13, 9,  align="right"),
    "section":     ParagraphRule("section",     16, 24),
    "sentence":    ParagraphRule("sentence",    14, 16, left_indent_chars=0),  # "□ 문장"
    "dash":        ParagraphRule("dash",        14, 12, left_indent_chars=3),  # "- 문장"
    "middot":      ParagraphRule("middot",      14, 12, left_indent_chars=5),  # "· 문장"
    "triangle":    ParagraphRule("triangle",    14, 12, left_indent_chars=7),  # "▷ 문장"
    "continued":   ParagraphRule("continued",   14, 0,  left_indent_chars=7),
    "continued_2": ParagraphRule("continued_2", 14, 16, left_indent_chars=7),
    "table_unit":  ParagraphRule("table_unit",  10, 0,  align="right"),
    "table_cell":  ParagraphRule("table_cell",  12, 0),
    "end_mark":    ParagraphRule("end_mark",    14, 0,  align="right"),
    "attachment":  ParagraphRule("attachment",  14, 0),
    "attach_title":ParagraphRule("attach_title",20, 20, bold=True, underline=True, align="center"),
    "page_number": ParagraphRule("page_number", 13, 0,  align="center"),
}


@dataclass(frozen=True)
class DocumentRule:
    margin_cm: float = 2.0
    line_spacing: float = 1.0
    font_name: str = "바탕체"
    char_spacing_pt: float = 0.0
    char_width_pct: int = 100
    use_footnote: bool = False

    header_top_cm: float = 0.7
    header_bottom_cm: float = 0.7

    table_border_pt: float = 0.5
    table_thick_border_pt: float = 1.5
    end_mark_text: str = "- 이 상 -"
    page_number_format: str = "- (별첨) {page}/{pages} -"


DOC = DocumentRule()


SYMBOL_MAP: dict[str, str] = {
    "＋": "+",
    "﹢": "+",
    "∼": "~",
    "～": "~",
    "・": "·",
    "•": "·",
    "‧": "·",
}


PREFIX_TO_KIND: dict[str, str] = {
    "□": "sentence",
    "-": "dash",
    "·": "middot",
    "▷": "triangle",
}
