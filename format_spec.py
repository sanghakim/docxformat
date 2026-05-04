"""표준 문서 포맷 스펙. 첨부 이미지의 양식을 그대로 옮긴 것."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParagraphRule:
    name: str
    font_size_pt: float
    space_after_pt: float
    left_indent_chars: int = 0
    bold: bool = False
    underline: bool = False
    align: str | None = None  # "left" | "center" | "right"


# 단락 종류별 규칙
RULES: dict[str, ParagraphRule] = {
    "title":       ParagraphRule("title",       20, 0,  bold=True, underline=True, align="center"),
    "date":        ParagraphRule("date",        13, 9,  align="right"),
    "section":     ParagraphRule("section",     16, 24),                       # "1. ㅇㅇㅇㅇ"
    "sentence":    ParagraphRule("sentence",    14, 16, left_indent_chars=0),  # "□ 문장"
    "dash":        ParagraphRule("dash",        14, 12, left_indent_chars=3),  # "- 문장"
    "middot":      ParagraphRule("middot",      14, 12, left_indent_chars=5),  # "· 문장"
    "triangle":    ParagraphRule("triangle",    14, 12, left_indent_chars=7),  # "▷ 문장"
    "continued":   ParagraphRule("continued",   14, 0,  left_indent_chars=7),  # 이어진 문장
    "continued_2": ParagraphRule("continued_2", 14, 16, left_indent_chars=7),  # 이어진 문장 둘째줄
    "table_unit":  ParagraphRule("table_unit",  10, 0,  align="right"),        # "(단위)"
    "table_cell":  ParagraphRule("table_cell",  12, 0),
    "end_mark":    ParagraphRule("end_mark",    14, 0,  align="right"),        # "- 이 상 -"
    "attachment":  ParagraphRule("attachment",  14, 0),                        # "별첨1"
    "attach_title":ParagraphRule("attach_title",20, 20, bold=True, underline=True, align="center"),
    "page_number": ParagraphRule("page_number", 13, 0,  align="center"),       # "- (별첨) 1/1 -"
}


@dataclass(frozen=True)
class DocumentRule:
    margin_cm: float = 2.0           # 상/하/좌/우
    line_spacing: float = 1.0        # 배수
    font_name: str = "바탕체"
    char_spacing_pt: float = 0.0     # 표준
    char_width_pct: int = 100        # 장평
    use_footnote: bool = False

    header_top_cm: float = 0.7
    header_bottom_cm: float = 0.7

    table_border_pt: float = 0.5             # 1/2 pt
    table_thick_border_pt: float = 1.5       # 1행 하단, 1열 우측
    end_mark_text: str = "- 이 상 -"
    page_number_format: str = "- (별첨) {page}/{pages} -"


DOC = DocumentRule()


# 부호 변환 규칙 (전각/유사 글리프 → 표준 ASCII/KS)
SYMBOL_MAP: dict[str, str] = {
    "＋": "+",
    "﹢": "+",
    "∼": "~",
    "～": "~",
    "・": "·",
    "•": "·",
    "‧": "·",
}


# 단락 시작 부호 → 분류 매핑
PREFIX_TO_KIND: dict[str, str] = {
    "□": "sentence",
    "-": "dash",
    "·": "middot",
    "▷": "triangle",
}
