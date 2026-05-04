"""문서/단락/표 포맷을 표준에 맞춰 수정. 변경된 항목을 Change 리스트로 반환."""
from __future__ import annotations

import re
from dataclasses import dataclass

from docx.document import Document as DocumentT
from docx.shared import Cm, Pt
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

UNIT_CELL_RE = re.compile(r"^\s*\([^)]{1,10}\)\s*$")


@dataclass
class Change:
    location: str
    field: str
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
        if section.header_distance and abs(section.header_distance.cm - DOC.header_top_cm) > 0.01:
            changes.append(Change(f"섹션 {i} header_distance", "header",
                                  f"{section.header_distance.cm}cm", f"{DOC.header_top_cm}cm"))
            section.header_distance = Cm(DOC.header_top_cm)
        if section.footer_distance and abs(section.footer_distance.cm - DOC.header_bottom_cm) > 0.01:
            changes.append(Change(f"섹션 {i} footer_distance", "footer",
                                  f"{section.footer_distance.cm}cm", f"{DOC.header_bottom_cm}cm"))
            section.footer_distance = Cm(DOC.header_bottom_cm)


def _set_run_font_name(run, name: str) -> None:
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rFonts.set(qn(f"w:{attr}"), name)


def _apply_run_format(run, rule: ParagraphRule, changes: list[Change], where: str) -> None:
    if (run.font.name or "") != DOC.font_name:
        changes.append(Change(where, "font_name", str(run.font.name), DOC.font_name))
        _set_run_font_name(run, DOC.font_name)

    target_size = Pt(rule.font_size_pt)
    if run.font.size != target_size:
        changes.append(Change(where, "font_size",
                              str(run.font.size.pt) if run.font.size else "?",
                              str(rule.font_size_pt)))
        run.font.size = target_size

    # bold/underline은 명시 규칙(title 계열)일 때만 강제
    if rule.bold is not None and bool(run.bold) != rule.bold:
        changes.append(Change(where, "bold", str(bool(run.bold)), str(rule.bold)))
        run.bold = rule.bold
    if rule.underline is not None and bool(run.underline) != rule.underline:
        changes.append(Change(where, "underline", str(bool(run.underline)), str(rule.underline)))
        run.underline = rule.underline


def _apply_paragraph_format(paragraph, rule: ParagraphRule, changes: list[Change],
                            where: str) -> None:
    """폰트/간격/정렬만 강제. 들여쓰기는 표준에 따라 공백 문자로 처리하므로 건드리지 않는다."""
    pf = paragraph.paragraph_format
    target_after = Pt(rule.space_after_pt)
    if pf.space_after != target_after:
        changes.append(Change(where, "space_after",
                              str(pf.space_after.pt) if pf.space_after else "?",
                              str(rule.space_after_pt)))
        pf.space_after = target_after

    if pf.line_spacing_rule != WD_LINE_SPACING.SINGLE:
        changes.append(Change(where, "line_spacing", str(pf.line_spacing_rule), "single"))
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE

    if rule.align and ALIGN_MAP[rule.align] != paragraph.alignment:
        changes.append(Change(where, "alignment", str(paragraph.alignment), rule.align))
        paragraph.alignment = ALIGN_MAP[rule.align]


def _apply_table_borders(table, changes: list[Change], where: str) -> None:
    """1행 하단·1열 우측만 1.5pt, 나머지는 0.5pt."""
    rows = table.rows
    if not rows:
        return

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


def _is_unit_cell(table, ri: int, ci: int) -> bool:
    """첫 행 우측 끝 셀이 '(...)' 패턴이면 단위 셀로 간주."""
    if ri != 0:
        return False
    rows = table.rows
    if not rows:
        return False
    n_cols = len(rows[0].cells)
    if ci != n_cols - 1:
        return False
    text = rows[0].cells[ci].text.strip()
    return bool(UNIT_CELL_RE.match(text))


def fix_document(doc: DocumentT) -> list[Change]:
    """문서 전체에 표준 포맷을 적용. 변경 리스트 반환."""
    changes: list[Change] = []

    _set_section_margins(doc, changes)

    body_paragraphs = doc.paragraphs
    prev_kind: str | None = None
    saw_attachment = False
    for idx, para in enumerate(body_paragraphs):
        kind = classify(para, prev_kind=prev_kind, saw_attachment=saw_attachment)
        if kind == "attachment":
            saw_attachment = True
        rule = RULES[kind]
        where = f"단락 {idx} ({kind})"
        _apply_paragraph_format(para, rule, changes, where)
        for run in para.runs:
            _apply_run_format(run, rule, changes, where)
        prev_kind = kind

    for ti, table in enumerate(doc.tables):
        _apply_table_borders(table, changes, f"표 {ti}")
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                kind = "table_unit" if _is_unit_cell(table, ri, ci) else "table_cell"
                rule = RULES[kind]
                for pi, para in enumerate(cell.paragraphs):
                    where = f"표 {ti} 셀({ri},{ci}) {kind}"
                    _apply_paragraph_format(para, rule, changes, where)
                    for run in para.runs:
                        _apply_run_format(run, rule, changes, where)

    return changes
