"""Streamlit UI: docx 업로드 → 검토 → 변경 미리보기 → 수정본 다운로드."""
from __future__ import annotations

import os
from io import BytesIO

import streamlit as st
from docx import Document

from checkers.format_checker import fix_document
from reviser import diffs_to_html, doc_to_bytes, revise_typos


st.set_page_config(page_title="공문서 포맷 검토 에이전트", layout="wide")
st.title("공문서 포맷·오타 검토 에이전트")
st.caption("표준 양식 준수 여부와 오탈자를 검토해 수정본을 만들어 드립니다.")

with st.sidebar:
    st.header("설정")
    engine = st.radio(
        "오타 검사 엔진",
        options=["claude", "rules"],
        format_func=lambda x: {
            "claude": "Claude API (정확도↑, ANTHROPIC_API_KEY 필요)",
            "rules": "규칙 엔진 (오프라인, 흔한 오탈자·공백 보정)",
        }[x],
    )
    do_format = st.checkbox("표준 포맷 적용", value=True)
    do_typo = st.checkbox("오타·부호 교정", value=True)
    if engine == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning("환경변수 ANTHROPIC_API_KEY가 설정되어 있지 않습니다.")

uploaded = st.file_uploader("검토할 .docx 파일 업로드", type=["docx"])

if uploaded and st.button("검토 시작", type="primary"):
    with st.spinner("문서 분석 중..."):
        doc = Document(BytesIO(uploaded.read()))

        format_changes = fix_document(doc) if do_format else []
        typo_diffs = revise_typos(doc, engine=engine) if do_typo else []
        out_bytes = doc_to_bytes(doc)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("포맷 변경 내역")
        if not format_changes:
            st.info("포맷 변경 사항 없음.")
        else:
            st.dataframe(
                [{"위치": c.location, "항목": c.field, "이전": c.before, "이후": c.after}
                 for c in format_changes],
                use_container_width=True,
            )

    with col2:
        st.subheader("오타·부호 변경 (트랙체인지 보기)")
        st.markdown(diffs_to_html(typo_diffs), unsafe_allow_html=True)

    st.divider()
    st.download_button(
        "수정본 다운로드 (변경 부분 파란색)",
        data=out_bytes,
        file_name=f"revised_{uploaded.name}",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
