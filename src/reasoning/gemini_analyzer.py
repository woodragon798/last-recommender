"""
Reasoning Layer - Gemini 버전 (MVP 무료 검증용)

- google-genai (신규 통합 SDK, pip install google-genai) 사용
- 구조는 analyzer.py(Claude 버전)와 동일한 2단계 호출 방식을 유지한다:
    1) research 단계: Google Search 그라운딩 도구를 켜고 후보 아이템의
       실제 진입조건을 검색해서 검증
    2) generate 단계: 검증된 근거 + 수집 데이터 + 이력(제외 목록)을 종합해서
       JSON 형식으로만 최종 5개 추천 생성
- 나중에 품질이 부족하면 이 파일만 analyzer.py(Claude)로 교체하면 되도록
  함수 시그니처(analyze(youtube_items, exclude_names) -> List[Dict])를
  동일하게 맞춰뒀다.

주의: 무료 티어 모델명/한도는 Google이 자주 바꾼다. 코드 돌리기 전
Google AI Studio(https://aistudio.google.com)의 Rate Limits 화면에서
현재 프로젝트 기준 최신 무료 모델명을 확인할 것.
"""
import json
import re
from typing import List, Dict

from src.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MAX_TOKENS, PERSONA_CONSTRAINTS


def _get_client():
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def _summarize_youtube_data(youtube_items: List[Dict], limit: int = 20) -> str:
    lines = []
    for item in youtube_items[:limit]:
        comments_preview = " / ".join(item.get("top_comments", [])[:2])
        lines.append(
            f"- 키워드[{item['source_keyword']}] 영상 \"{item['title']}\" "
            f"(채널: {item['channel']}, 조회수: {item['view_count']:,}, "
            f"댓글수: {item['comment_count']:,})"
            + (f" | 반응 예시: {comments_preview}" if comments_preview else "")
        )
    return "\n".join(lines) if lines else "(수집된 유튜브 데이터 없음)"


def _research_phase(client, youtube_summary: str) -> str:
    """1단계: Google Search 그라운딩으로 후보 아이템의 실제 조건 검증"""
    from google.genai import types

    prompt = (
        "당신은 한국 시장에 정통한 사업 리서처입니다. 아래 유튜브 트렌드 데이터를 보고, "
        "여기서 파생될 수 있는 부업/사업 아이템 후보들을 떠올린 뒤, Google 검색으로 "
        "각 후보의 실제 진입 조건(초기 자본, 필요 장비, 플랫폼 수수료, 최근 규제 변화, "
        "실제 후기 상 수익성)을 검증하세요. 확인된 사실만 정리하고, 확인 안 된 것은 "
        "'확인 필요'라고 명시하세요.\n\n"
        f"## 오늘의 유튜브 트렌드 데이터\n{youtube_summary}\n\n"
        "위 데이터를 참고해서 관련 사업/부업 후보 6~8개를 찾고, 각각의 실제 "
        "진입조건을 검색해서 검증한 결과를 정리해줘."
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            max_output_tokens=GEMINI_MAX_TOKENS,
        ),
    )
    return response.text or ""


def _generate_phase(client, youtube_summary: str, research_notes: str,
                     exclude_names: List[str]) -> List[Dict]:
    """2단계: 검증된 근거를 바탕으로 JSON 형식 5개 추천 생성"""
    from google.genai import types

    exclude_text = ", ".join(exclude_names) if exclude_names else "(없음)"
    persona = PERSONA_CONSTRAINTS

    prompt = (
        "반드시 JSON 배열만 출력하세요. 설명, 코드블록 표시(```), 그 어떤 부가 텍스트도 "
        "포함하지 마세요. 출력은 아래 스키마를 가진 객체 5개로 구성된 JSON 배열이어야 합니다:\n"
        "{\n"
        '  "name": "아이템 이름",\n'
        '  "category": "카테고리",\n'
        '  "description": "2~3문장 설명",\n'
        '  "why_now": "왜 지금 이 트렌드와 관련있는지 (데이터 근거 포함)",\n'
        '  "awareness_level": "낮음 | 보통 | 높음",\n'
        '  "capital_required": "예상 초기 자본 (예: 무자본, 5만원 이하 등)",\n'
        '  "physical_involvement": "신체를 어떻게 활용하는지",\n'
        '  "income_stability_score": 1~5 (숫자),\n'
        '  "feasibility_score": 1~5 (숫자),\n'
        '  "first_week_actions": ["1주차에 할 일 1", "할 일 2", "할 일 3"]\n'
        "}\n\n"
        f"## 대상\n{persona['target']}\n"
        f"## 보유 자산\n{', '.join(persona['assets'])}\n"
        f"## 조건\n"
        f"- 초기 자본: {persona['capital']}\n"
        f"- 목표: {persona['profit_goal']} (한 방의 대박 아이템 제외)\n"
        f"- 이미 알려진 아이템이어도 '인지도가 낮은 실행 방식'이면 추천 가능\n"
        f"- 최근 추천했던 아이템은 제외: {exclude_text}\n\n"
        f"## 오늘의 유튜브 트렌드 데이터\n{youtube_summary}\n\n"
        f"## 리서치 검증 결과\n{research_notes}\n\n"
        f"위 내용을 종합해서 조건에 맞는 사업 아이템 {persona['num_recommendations']}개를 "
        f"JSON 배열로만 출력해줘."
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=GEMINI_MAX_TOKENS,
            response_mime_type="application/json",  # Gemini에 JSON 강제 (도구 미사용 시 지원)
        ),
    )
    raw_text = (response.text or "").strip()

    # response_mime_type이 무시되는 경우를 대비한 방어적 파싱
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text, flags=re.MULTILINE).strip()

    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{raw_text}"
        )

    if not isinstance(items, list):
        raise ValueError("Gemini 응답이 JSON 배열 형식이 아닙니다.")

    return items


def analyze(youtube_items: List[Dict], exclude_names: List[str]) -> List[Dict]:
    client = _get_client()
    youtube_summary = _summarize_youtube_data(youtube_items)

    research_notes = _research_phase(client, youtube_summary)
    items = _generate_phase(client, youtube_summary, research_notes, exclude_names)

    return items
