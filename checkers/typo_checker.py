"""오타 검사. 엔진 선택: 'claude' (AI) 또는 'rules' (정규식)."""
from __future__ import annotations

import json
import os
import re
from typing import Literal

Engine = Literal["claude", "rules"]


SYSTEM_PROMPT = (
    "너는 한국 공문서 교정 전문가다. 입력 단락 목록을 검토해 오탈자, 띄어쓰기, "
    "맞춤법 오류만 최소한으로 수정한다. 의미와 문체는 절대 바꾸지 않는다. "
    "고유명사·영문·숫자는 그대로 둔다. "
    "응답은 반드시 JSON: {\"items\":[{\"index\":n,\"corrected\":\"...\"}]} 형식. "
    "수정이 없는 항목은 corrected에 원문을 그대로 넣는다."
)


# 흔한 한국어 오탈자 (사전식). key=잘못된 표현, value=올바른 표현.
COMMON_TYPOS: dict[str, str] = {
    "됬": "됐",
    "됫": "됐",
    "왠만": "웬만",
    "어떻해": "어떡해",
    "역활": "역할",
    "오랫만": "오랜만",
    "예기": "얘기",
    "일찌기": "일찍이",
    "할려고": "하려고",
    "않하": "안 하",
    "몇일": "며칠",
    "갯수": "개수",
    "촛점": "초점",
    "넓다란": "널따란",
}


# 영문 단어 안의 숫자/문자 혼동 (CE0 → CEO 등)
ACRONYM_FIX: dict[str, str] = {
    r"\bCE0\b": "CEO",
    r"\bCT0\b": "CTO",
    r"\bCF0\b": "CFO",
    r"\bC00\b": "COO",
}


def _apply_rules(text: str) -> str:
    """오타 사전·약어 혼동만 보정. 공백 정렬은 건드리지 않는다."""
    out = text
    for wrong, right in COMMON_TYPOS.items():
        out = out.replace(wrong, right)
    for pat, repl in ACRONYM_FIX.items():
        out = re.sub(pat, repl, out)
    return out


def _check_with_rules(paragraphs: list[str]) -> list[str]:
    return [_apply_rules(t) for t in paragraphs]


def _check_with_claude(paragraphs: list[str]) -> list[str]:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    payload = [{"index": i, "text": t} for i, t in enumerate(paragraphs) if t.strip()]
    if not payload:
        return list(paragraphs)

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    raw = msg.content[0].text
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start : end + 1])

    out = list(paragraphs)
    for item in data.get("items", []):
        idx = item["index"]
        if 0 <= idx < len(out):
            out[idx] = item["corrected"]
    return out


def correct_paragraphs(paragraphs: list[str], engine: Engine = "claude") -> list[str]:
    if engine == "claude":
        return _check_with_claude(paragraphs)
    if engine == "rules":
        return _check_with_rules(paragraphs)
    raise ValueError(f"unknown engine: {engine}")
