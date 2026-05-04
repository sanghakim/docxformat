"""문서/단락/표 포맷을 표준에 맞춰 수정. 변경된 항목을 Change 리스트로 반환."""
from __future__ import annotations

from dataclasses import dataclass

from docx import Document
from docx.document import Document as DocumentT
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from classifier import classify
from format_spec import DOC, RULES, ParagraphRule


ALIGN_MAP = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}


@dataclass
class Change:
    location: str            # "문서 여백", "단락 3", "표 1 셀(0,0)" 등
    field: str               # "font_size", "space_after", ...
    before: str
    after: str


def _set_section_margins(doc: DocumentT, changes: list[Change]) -> None:
    target = Cm(DOC.margin_cm)
    for i, section in enumerate(doc.sections):
        for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
            current = getattr(section, attr)
            if current is None or abs(current.cm - DOC.margin_cm) > 0.01:
                changes.append(Change(f"섹션 {i} {attr}", "margin",
                                      f"{current.cm if current else '?'}cm",
                                      f"{DOC.margin_cm}cm"))
                setattr(section, attr, target)
        # 머리글 위/아래 0.7cm
        if abs(section.header_distance.cm - DOC.header_top_cm) > 0.01:
            changes.append(Change(f"섹션 {i} header_distance", "header",
                                  f"{section.header_distance.cm}cm", f"{DOC.header_top_cm}cm"))
            section.header_distance = Cm(DOC.header_top_cm)
        if abs(section.footer_distance.cm - DOC.header_bottom_cm) > 0.01:
            changes.append(Change(f"섹션 {i} footer_distance", "footer",
                                  f"{section.footer_distance.cm}cm", f"{DOC.header_bottom_cm}cm"))
            section.footer_distance = Cm(DOC.header_bottom_cm)


def _apply_run_format(run, rule: ParagraphRule, changes: list[Change], where: str) -> None:
    if run.font.name != DOC.font_name:
        changes.append(Change(where, "font_name", str(run.font.name), DOC.font_name))
        run.font.name = DOC.font_name
        # 한글 폰트(eastAsia) 같이 설정
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.append(rFonts)
        rFonts.set(qn("w:eastAsia"), DOC.font_name)
        rFonts.set(qn("w:ascii"), DOC.font_name)
        rFonts.set(qn("w:hAnsi"), DOC.font_name)

    target_size = Pt(rule.font_size_pt)
    if run.font.size != target_size:
        changes.append(Change(where, "font_size",
                              str(run.font.size.pt) if run.font.size else "?",
                              str(rule.font_size_pt)))
        run.font.size = target_size

    if bool(run.bold) != rule.bold:
        changes.append(Change(where, "bold", str(bool(run.bold)), str(rule.bold)))
        run.bold = rule.bold

    if bool(run.underline) != rule.underline:
        changes.append(Change(where, "underline", str(bool(run.underline)), str(rule.underline)))
        run.underline = rule.underline


def _apply_paragraph_format(paragraph, rule: ParagraphRule, changes: list[Change], where: str) -> None:
    pf = paragraph.paragraph_format
    target_after = Pt(rule.space_after_pt)
    if pf.space_after != target_after:
        changes.append(Change(where, "space_after",
                              str(pf.space_after.pt) if pf.space_after else "?",
                              str(rule.space_after_pt)))
        pf.space_after = target_after

    # 줄간격 1.0 배수
    if pf.line_spacing_rule != WD_LINE_SPACING.SINGLE:
        changes.append(Change(where, "line_spacing", str(pf.line_spacing_rule), "single"))
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE

    # 들여쓰기: "칸"을 폰트 크기 기준 글자폭으로 환산 (대략 14pt 기준 0.5cm/글자)
    if rule.left_indent_chars:
        target_indent = Cm(0.5 * rule.left_indent_chars)
        if pf.left_indent != target_indent:
            changes.append(Change(where, "left_indent",
                                  str(pf.left_indent.cm) if pf.left_indent else "0",
                                  f"{target_indent.cm}cm"))
            pf.left_indent = target_indent

    if rule.align and ALIGN_MAP[rule.align] != paragraph.alignment:
        changes.append(Change(where, "alignment", str(paragraph.alignment), rule.align))
        paragraph.alignment = ALIGN_MAP[rule.align]


def _apply_table_borders(table, changes: list[Change], where: str) -> None:
    """1행 하단·1열 우측만 1.5pt, 나머지는 0.5pt."""
    rows = table.rows
    if not rows:
        return
    n_rows = len(rows)
    n_cols = len(rows[0].cells)

    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row.cells):
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = tcPr.find(qn("w:tcBorders"))
            if tcBorders is None:
                tcBorders = OxmlElement("w:tcBorders")
                tcPr.append(tcBorders)
            for edge in ("top", "left", "bottom", "right"):
                el = tcBorders.find(qn(f"w:{edge}"))
                if el is None:
                    el = OxmlElement(f"w:{edge}")
                    tcBorders.append(el)
                thick = (ri == 0 and edge == "bottom") or (ci == 0 and edge == "right")
                size = "12" if thick else "4"  # 1/8 pt 단위 → 4=0.5pt, 12=1.5pt
                el.set(qn("w:val"), "single")
                el.set(qn("w:sz"), size)
                el.set(qn("w:color"), "000000")
    changes.append(Change(where, "borders", "?", "0.5pt + 1행하단/1열우측 1.5pt"))


def fix_document(doc: DocumentT) -> list[Change]:
    """문서 전체에 표준 포맷을 적용. 변경 리스트 반환."""
    changes: list[Change] = []

    _set_section_margins(doc, changes)

    body_paragraphs = doc.paragraphs
    for idx, para in enumerate(body_paragraphs):
        kind = classify(para.text, is_first=(idx == 0))
        rule = RULES[kind]
        where = f"단락 {idx} ({kind})"
        _apply_paragraph_format(para, rule, changes, where)
        for run in para.runs:
            _apply_run_format(run, rule, changes, where)

    for ti, table in enumerate(doc.tables):
        _apply_table_borders(table, changes, f"표 {ti}")
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                for pi, para in enumerate(cell.paragraphs):
                    rule = RULES["table_cell"]
                    where = f"표 {ti} 셀({ri},{ci}) 단락 {pi}"
                    _apply_paragraph_format(para, rule, changes, where)
                    for run in para.runs:
                        _apply_run_format(run, rule, changes, where)

    return changes
