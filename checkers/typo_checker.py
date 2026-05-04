"""오타 검사. 엔진 선택: Claude API 또는 hanspell."""
from __future__ import annotations

import json
import os
from typing import Literal

Engine = Literal["claude", "hanspell"]


SYSTEM_PROMPT = (
    "너는 한국 공문서 교정 전문가다. 입력된 단락 목록을 검토해 오탈자, 띄어쓰기, "
    "맞춤법 오류만 최소한으로 수정한다. 의미와 문체는 절대 바꾸지 않는다. "
    "각 단락에 대해 corrected 텍스트만 반환한다. "
    "응답은 반드시 JSON: {\"items\":[{\"index\":n,\"corrected\":\"...\"}]} 형식."
)


def _check_with_claude(paragraphs: list[str]) -> list[str]:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    payload = [{"index": i, "text": t} for i, t in enumerate(paragraphs) if t.strip()]
    if not payload:
        return list(paragraphs)

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    raw = msg.content[0].text
    # JSON 블록 추출
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start : end + 1])

    out = list(paragraphs)
    for item in data.get("items", []):
        idx = item["index"]
        if 0 <= idx < len(out):
            out[idx] = item["corrected"]
    return out


def _check_with_hanspell(paragraphs: list[str]) -> list[str]:
    from hanspell import spell_checker

    out = []
    for text in paragraphs:
        if not text.strip():
            out.append(text)
            continue
        try:
            result = spell_checker.check(text)
            out.append(result.checked)
        except Exception:
            out.append(text)
    return out


def correct_paragraphs(paragraphs: list[str], engine: Engine = "claude") -> list[str]:
    if engine == "claude":
        return _check_with_claude(paragraphs)
    if engine == "hanspell":
        return _check_with_hanspell(paragraphs)
    raise ValueError(f"unknown engine: {engine}")
