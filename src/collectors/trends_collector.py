"""
Step 1. Google Trends Collector
- 한국 일별 급상승 검색어 + 연관 키워드를 수집한다.
- pytrends는 비공식 라이브러리라 구글이 페이지 구조를 바꾸면 깨질 수 있다(SPOF).
  → 실패 시 예외를 삼키지 않고 None을 반환해서, 호출부(main.py)가
    반드시 폴백 경로(YouTube mostPopular)로 전환하도록 강제한다.
- '실패를 숨기지 않는다'는 설계 원칙: 성공 여부를 status 필드로 명시한다.
"""
from typing import Optional
from src.config import TRENDS_GEO, RELEVANT_CATEGORY_HINTS, MAX_TREND_KEYWORDS


def _is_relevant(keyword: str) -> bool:
    """카테고리 힌트와 겹치는지 아주 단순한 문자열 매칭으로 1차 필터링.
    (정교한 분류는 Reasoning Layer의 Claude에게 맡긴다 — 여기서는 명백히
     무관한 키워드(연예인 이슈, 스포츠 결과 등)만 걸러내는 용도)"""
    return any(hint in keyword for hint in RELEVANT_CATEGORY_HINTS)


def collect_trend_keywords() -> Optional[dict]:
    """
    Returns:
        성공 시: {"status": "ok", "keywords": [...], "raw_count": int}
        실패 시: None  (호출부에서 폴백 처리)
    """
    try:
        from pytrends.request import TrendReq  # 지연 임포트: 없어도 나머지 모듈은 동작
    except ImportError:
        print("[trends_collector] pytrends가 설치되어 있지 않습니다. 폴백으로 전환합니다.")
        return None

    try:
        pytrends = TrendReq(hl="ko-KR", tz=540)  # tz=540 => UTC+9 (KST)

        # 1) 오늘의 실시간 급상승 검색어 (한국)
        trending_df = pytrends.trending_searches(pn="south_korea")
        raw_keywords = trending_df[0].tolist() if not trending_df.empty else []

        collected = set()

        # 2) 급상승 검색어 중 관련성 있는 것 우선 채택
        for kw in raw_keywords:
            if _is_relevant(kw):
                collected.add(kw)

        # 3) 부족하면 관련 카테고리 힌트 자체를 seed로 넣어 related_queries 확장
        seed_terms = RELEVANT_CATEGORY_HINTS[:3]
        for seed in seed_terms:
            if len(collected) >= MAX_TREND_KEYWORDS:
                break
            try:
                pytrends.build_payload([seed], timeframe="now 7-d", geo=TRENDS_GEO)
                related = pytrends.related_queries().get(seed, {})
                rising = related.get("rising")
                if rising is not None and not rising.empty:
                    for q in rising["query"].tolist():
                        collected.add(q)
                        if len(collected) >= MAX_TREND_KEYWORDS:
                            break
            except Exception as e:
                # 개별 seed 실패는 전체 실패로 취급하지 않고 건너뛴다
                print(f"[trends_collector] related_queries 실패 (seed={seed}): {e}")
                continue

        keywords = list(collected)[:MAX_TREND_KEYWORDS]

        if not keywords:
            # 라이브러리는 동작했지만 관련 키워드가 하나도 안 나온 경우도
            # 데이터 품질 실패로 보고 폴백을 유도한다.
            print("[trends_collector] 관련 키워드 0건. 폴백으로 전환합니다.")
            return None

        return {"status": "ok", "keywords": keywords, "raw_count": len(raw_keywords)}

    except Exception as e:
        print(f"[trends_collector] 수집 실패: {e}")
        return None
