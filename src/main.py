"""
Main Orchestrator
- 화이트보드에서 그린 전체 흐름을 그대로 코드로 옮긴 것.

  Trigger(GitHub Actions) → Collection(Trends → YouTube) → History →
  Reasoning(Claude) → Output(docx) → History 저장

- 실패 처리 원칙: Google Trends가 실패해도 파이프라인 전체를 죽이지 않고
  YouTube mostPopular로 자동 전환한다(Graceful Degradation). 단, 어떤
  경로로 실행됐는지는 리포트에 항상 명시한다.
"""
import sys

from src.collectors import trends_collector, youtube_collector
from src.history import history_manager
from src.reasoning import gemini_analyzer as analyzer  # MVP: Gemini 무료 API 사용
# 나중에 Claude로 바꾸고 싶으면 위 줄을:
#   from src.reasoning import analyzer
# 로 바꾸면 됩니다 (인터페이스 동일: analyze(youtube_items, exclude_names))
from src.output import report_generator


def run() -> str:
    # ── Step 1: 트렌드 수집 시도 ──────────────────────────────────
    trend_result = trends_collector.collect_trend_keywords()

    if trend_result is not None:
        data_source_status = "ok"
        keywords = trend_result["keywords"]
        print(f"[main] 트렌드 수집 성공. 키워드: {keywords}")
        youtube_items = youtube_collector.collect_by_keywords(keywords)
    else:
        data_source_status = "fallback"
        print("[main] 트렌드 수집 실패 → YouTube mostPopular로 폴백합니다.")
        youtube_items = youtube_collector.collect_most_popular()

    if not youtube_items:
        print("[main] 유튜브 데이터도 비어있습니다. 파이프라인을 중단합니다.")
        sys.exit(1)

    # ── Step 2: 이력 로드 (중복 방지용 제외 목록) ──────────────────
    history = history_manager.load_history()
    exclude_names = history_manager.get_recent_item_names(history)
    print(f"[main] 최근 제외 대상 {len(exclude_names)}건")

    # ── Step 3: Claude 분석 → 5개 추천 생성 ────────────────────────
    items = analyzer.analyze(youtube_items, exclude_names)
    print(f"[main] {len(items)}개 아이템 생성 완료")

    # ── Step 4: 리포트 생성 ────────────────────────────────────────
    filepath = report_generator.generate_report(items, data_source_status)
    print(f"[main] 리포트 저장 완료: {filepath}")

    # ── Step 5: 이력 갱신 ──────────────────────────────────────────
    history = history_manager.append_today(history, items, data_source_status)
    history_manager.save_history(history)
    print("[main] 이력 갱신 완료")

    return filepath


if __name__ == "__main__":
    run()
