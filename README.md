# 매일 사업 아이템 추천 시스템

한국 유튜브/구글 트렌드를 분석해서, "컴퓨터 1대 + 건강한 신체"만으로 시작할 수 있는
사업 아이템을 매일 정해진 시간에 5개씩 추천하는 완전 자동화 파이프라인입니다.

## 전체 구조

```
GitHub Actions (매일 08:00 KST)
   → Google Trends 수집 (실패 시 YouTube 인기차트로 자동 폴백)
   → YouTube Data API로 관련 영상/댓글 수집
   → 이력(history.json) 대조로 중복 제거
   → Gemini API 2단계 호출 (리서치 검증 → JSON 5개 생성)   ← MVP: 무료 티어 사용
   → .docx 리포트 생성 + 저장소에 커밋 + 아티팩트 업로드
```

> **MVP 버전**: Reasoning Layer는 현재 Gemini 무료 API(`src/reasoning/gemini_analyzer.py`)를
> 사용합니다. 품질이 부족하다고 느껴지면 `src/main.py`의 import 한 줄만 바꿔서
> 언제든 Claude API 버전(`src/reasoning/analyzer.py`)으로 전환할 수 있습니다.

## 사전 준비

1. **이 폴더를 GitHub 저장소로 만들기** (private 권장)
2. **API 키 발급**
   - YouTube Data API v3 키: [Google Cloud Console](https://console.cloud.google.com/)에서 발급
   - Gemini API 키: [Google AI Studio](https://aistudio.google.com/)에서 무료 발급
     (실행 전 Rate Limits 화면에서 현재 무료 티어 모델명/한도를 반드시 확인하세요.
     Google이 자주 정책을 바꿉니다 — Pro 계열은 유료 전환된 경우가 많고,
     Flash/Flash-Lite 계열 위주로 무료 한도가 남아있습니다.)
3. **GitHub Secrets 등록** (저장소 Settings → Secrets and variables → Actions)
   - `YOUTUBE_API_KEY`
   - `GEMINI_API_KEY`
4. 저장소에 push하면 워크플로우가 자동으로 매일 실행됩니다.
   (`.github/workflows/daily-recommendation.yml`의 `workflow_dispatch`로 수동 실행도 가능)

## 로컬에서 테스트하기

```bash
pip install -r requirements.txt
export YOUTUBE_API_KEY="your_key"
export GEMINI_API_KEY="your_key"
python -m src.main
```

실행 후 `output_reports/business_recommendation_YYYY-MM-DD.docx` 파일이 생성됩니다.

## 설계 상 알아둘 점

- **Google Trends는 비공식 API입니다.** `pytrends`가 구글 페이지 구조 변경으로
  깨질 수 있습니다(단일 장애점). 이 경우 시스템은 죽지 않고 YouTube
  `mostPopular` 차트로 자동 전환하며, 리포트 상단에 "폴백 모드"라고 표시합니다.
  폴백 모드에서는 트렌드 신선도가 평소보다 낮을 수 있다는 점을 참고하세요.
- **API 할당량**: YouTube search.list는 1회당 100 units, 일일 한도 10,000 units입니다.
  트렌드로 압축된 키워드(기본 8개)만 검색하므로 하루 약 800 units만 사용하고,
  나머지는 댓글 수집 등에 여유롭게 씁니다. (`src/config.py`의 `MAX_TREND_KEYWORDS`로 조정)
- **중복 방지**: 최근 30일간 추천된 아이템명은 `data/history.json`에 저장되어
  다음 추천 시 제외 목록으로 전달됩니다. (`HISTORY_RETENTION_DAYS`로 조정)
- **인지도 낮은 아이템도 허용**: 이미 널리 알려진 카테고리라도, Claude가
  "인지도가 낮은 실행 방식"이라 판단하면 추천에 포함되도록 프롬프트에 명시했습니다.
  각 추천 항목의 `awareness_level` 필드로 확인할 수 있습니다.
- **5개 추천 + 최종 선택은 사용자 몫**: 시스템은 우선순위를 정해주지 않고,
  5개를 병렬로 제시합니다. 어떤 걸 실행할지는 리포트를 보고 직접 결정하시면 됩니다.

## Gemini(무료) ↔ Claude(유료) 전환

`src/reasoning/` 폴더에 두 버전이 모두 들어있습니다:
- `gemini_analyzer.py` — 현재 기본값. 무료지만 하루 요청 한도가 모델별로
  다르고(적으면 하루 수십 회 수준), Flash 계열이라 리서치 검증 품질이
  Claude 대비 다소 얕을 수 있습니다.
- `analyzer.py` — Claude(Sonnet) 버전. 유료지만(하루 2회 호출 기준 월 몇천 원 수준)
  웹서치 검증과 조건 필터링 품질이 더 안정적입니다.

전환은 `src/main.py`의 이 부분만 바꾸면 됩니다:
```python
from src.reasoning import gemini_analyzer as analyzer   # 현재: Gemini
# from src.reasoning import analyzer                    # 전환: Claude
```
그리고 GitHub Secrets에 `ANTHROPIC_API_KEY`를 등록하고, 워크플로우 파일의
`env:` 섹션에 `ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}`를 추가하세요.

## 다음에 고도화할 만한 부분

- `awareness_level`, `feasibility_score` 등 스코어링 기준의 정확도는 결국
  Claude의 판단에 의존합니다. 실제로 아이템을 실행해본 뒤 결과를 다시
  히스토리에 기록해서, 다음 추천 때 "실제로 효과 있었던 카테고리"에
  가중치를 주는 피드백 루프를 추가할 수 있습니다.
- 알림 채널(카카오톡/텔레그램)을 나중에 원하면 Output Layer 뒤에
  전송 단계만 추가하면 됩니다. 지금은 파일 저장까지만 구현되어 있습니다.

## 면책 조항

이 시스템이 생성하는 추천은 자동화된 참고 자료이며, 투자·창업 조언이 아닙니다.
실행 여부와 최종 판단은 반드시 본인이 직접 검토한 뒤 결정하세요.
