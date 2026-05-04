# 공문서 포맷·오타 검토 에이전트

`.docx` 문서를 업로드하면 표준 양식 준수 여부를 검사·수정하고, 오타를 교정해
수정본을 다운로드할 수 있는 Streamlit 앱입니다.

## 표준 포맷 (요약)

- 여백: 상/하/좌/우 2cm, 글꼴 바탕체, 줄간격 1.0, 장평 100%, 각주 미사용
- 제목 20pt 볼드/밑줄, 소제목 16pt, 문장 14pt
- 들여쓰기: `-` 3칸, `·` 5칸, `▷` 7칸
- 표: 0.5pt 테두리, 1행 하단·1열 우측만 1.5pt 굵은선, 표 안 12pt
- 본문 끝 `- 이 상 -` 우측 정렬, 머리글 쪽번호 `- (별첨) 1/1 -`
- 부호 변환: `＋→+`, `∼/～→~`, `・/•→·`

자세한 규칙은 `format_spec.py` 참고.

## 실행

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # Claude 엔진 사용 시
streamlit run app.py
```

## 변경 표시 방식

- **UI**: 트랙체인지 스타일로 삽입(파란 밑줄)/삭제(빨간 취소선)을 함께 표시
- **다운로드 .docx**: 변경된 부분만 파란색(#0000FF) 폰트로 표시

## 모듈 구조

```
app.py                    # Streamlit UI
format_spec.py            # 표준 포맷 규칙 (dataclass)
classifier.py             # 단락 종류 판별
checkers/
  format_checker.py       # 여백/폰트/표 테두리 등 검사·수정
  symbol_checker.py       # 부호 정규화
  typo_checker.py         # 오타 검사 (claude / hanspell)
reviser.py                # 단락 diff 생성, 파란색 마킹, 트랙체인지 HTML
```
