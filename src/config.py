"""
환경설정 모듈
- 모든 API 키와 튜닝 가능한 상수를 한 곳에 모아둔다.
- 실제 값은 환경변수(GitHub Actions Secrets 또는 로컬 .env)에서 읽는다.
"""
import os

# ── API 키 ────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# 나중에 Claude로 다시 전환하고 싶을 때를 대비해 남겨둠 (src/reasoning/analyzer.py)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── 지역/언어 ─────────────────────────────────────────────────────
REGION_CODE = "KR"
TRENDS_GEO = "KR"          # pytrends geo 코드
TRENDS_LANG = "ko"

# ── 페르소나 / 제약 조건 (Reasoning Layer 프롬프트에 그대로 들어감) ──
PERSONA_CONSTRAINTS = {
    "target": "20대 초반 남성",
    "assets": ["컴퓨터 1대", "건강한 신체"],
    "capital": "무자본 또는 최소 자본",
    "profit_goal": "대박보다는 꾸준하고 안정적인 소액 수익",
    "num_recommendations": 5,
    "allow_known_items": True,   # 이미 알려진 아이템이어도 '인지도가 낮으면' 추천 허용
}

# ── 트렌드 1차 필터링 키워드 (구글 트렌드 결과 중 이 카테고리와 관련된 것만 통과) ──
RELEVANT_CATEGORY_HINTS = [
    "부업", "재테크", "알바", "아르바이트", "자기계발", "노하우", "돈벌기",
    "부수입", "사이드잡", "1인", "무자본", "챌린지", "꿀팁", "창업",
]

# ── 수집 규모 ─────────────────────────────────────────────────────
MAX_TREND_KEYWORDS = 8          # 구글 트렌드에서 1차로 남길 키워드 수
MAX_VIDEOS_PER_KEYWORD = 5      # 키워드당 유튜브 영상 수집 수
MAX_COMMENTS_PER_VIDEO = 5      # 영상당 상위 댓글 수집 수
HISTORY_RETENTION_DAYS = 30     # 중복 방지용 이력 보관 기간

# ── 파일 경로 ─────────────────────────────────────────────────────
HISTORY_FILE = os.environ.get("HISTORY_FILE", "data/history.json")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output_reports")

# ── Claude 모델 설정 (analyzer.py, 현재는 미사용 - 백업용) ─────────
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
CLAUDE_MAX_TOKENS = 4000

# ── Gemini 모델 설정 (gemini_analyzer.py, 현재 기본 사용) ──────────
# 주의: 무료 티어 대상 모델명은 Google이 자주 바꾼다.
# 실행 전 https://aistudio.google.com 의 Rate Limits 화면에서 최신 무료
# 모델명을 확인하고 필요시 환경변수 GEMINI_MODEL로 덮어쓸 것.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_MAX_TOKENS = 4000
