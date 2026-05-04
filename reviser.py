"""오타 교정을 단락에 적용. 단락 단위 diff 생성과 두 가지 출력:
- UI용 트랙체인지 HTML (삽입은 파란 밑줄, 삭제는 빨간 취소선)
- 다운로드용 .docx (변경된 run을 파란색 폰트로 마킹)
"""
from __future__ import annotations

import difflib
import html
from dataclasses import dataclass
from io import BytesIO

from docx.document import Document as DocumentT
from docx.shared import RGBColor

from checkers.hanja_converter import to_hangul
from checkers.symbol_checker import normalize_symbols
from checkers.typo_checker import Engine, correct_paragraphs


BLUE = RGBColor(0x00, 0x00, 0xFF)


@dataclass
class ParagraphDiff:
    index: int
    before: str
    after: str
    ops: list[tuple[str, str]]  # [("equal"|"insert"|"delete"|"replace", segment)]


def _diff_ops(before: str, after: str) -> list[tuple[str, str]]:
    sm = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    ops: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            ops.append(("equal", before[i1:i2]))
        elif tag == "delete":
            ops.append(("delete", before[i1:i2]))
        elif tag == "insert":
            ops.append(("insert", after[j1:j2]))
        elif tag == "replace":
            ops.append(("delete", before[i1:i2]))
            ops.append(("insert", after[j1:j2]))
    return ops


def revise_typos(doc: DocumentT, engine: Engine,
                 *, convert_hanja: bool = True) -> list[ParagraphDiff]:
    """본문 + 표 셀 단락에 부호 변환 → 한자 변환 → 오타 교정 순으로 적용."""
    targets: list = []
    for para in doc.paragraphs:
        targets.append(para)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    targets.append(para)

    originals = [p.text for p in targets]

    # 1) 부호 정규화
    stage = [normalize_symbols(t)[0] for t in originals]
    # 2) 한자 → 한글
    if convert_hanja:
        stage = [to_hangul(t)[0] for t in stage]
    # 3) 오타 교정
    stage = correct_paragraphs(stage, engine=engine)

    diffs: list[ParagraphDiff] = []
    for idx, (para, before, after) in enumerate(zip(targets, originals, stage)):
        if before == after:
            continue
        diffs.append(ParagraphDiff(idx, before, after, _diff_ops(before, after)))
        _rewrite_paragraph_blue(para, before, after)

    return diffs


def _rewrite_paragraph_blue(paragraph, before: str, after: str) -> None:
    """단락 텍스트를 'after'로 바꾸되, 변경된 부분만 파란색 run으로 만든다.
    기존 run의 서식(폰트/크기 등)은 첫 run에서 가져와 보존한다."""
    template_run = paragraph.runs[0] if paragraph.runs else None
    font_name = template_run.font.name if template_run else None
    font_size = template_run.font.size if template_run else None
    bold = template_run.bold if template_run else None
    underline = template_run.underline if template_run else None

    # 기존 run 모두 제거
    for r in list(paragraph.runs):
        r._element.getparent().remove(r._element)

    for tag, segment in _diff_ops(before, after):
        if tag == "delete":
            continue  # 다운로드 파일에는 삭제 흔적 남기지 않음
        run = paragraph.add_run(segment)
        if font_name:
            run.font.name = font_name
        if font_size:
            run.font.size = font_size
        if bold is not None:
            run.bold = bold
        if underline is not None:
            run.underline = underline
        if tag == "insert":
            run.font.color.rgb = BLUE


def diffs_to_html(diffs: list[ParagraphDiff]) -> str:
    """Streamlit에 보여줄 트랙체인지 스타일 HTML."""
    if not diffs:
        return "<p><em>변경 사항이 없습니다.</em></p>"

    parts = ["<style>",
             ".ins{color:#0000FF;text-decoration:underline;}",
             ".del{color:#C00000;text-decoration:line-through;}",
             ".eq{color:#222;}",
             ".para{padding:6px 0;border-bottom:1px solid #eee;font-family:serif;}",
             ".loc{color:#888;font-size:12px;}",
             "</style>"]
    for d in diffs:
        parts.append(f'<div class="para"><div class="loc">단락 #{d.index}</div>')
        for tag, seg in d.ops:
            esc = html.escape(seg).replace("\n", "<br>")
            cls = {"equal": "eq", "insert": "ins", "delete": "del"}[tag]
            parts.append(f'<span class="{cls}">{esc}</span>')
        parts.append("</div>")
    return "".join(parts)


def doc_to_bytes(doc: DocumentT) -> bytes:
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
