"""
Step 2. YouTube Collector
- 정상 경로: Google Trends에서 압축된 키워드로만 search.list 호출 (할당량 절약)
- 폴백 경로: 트렌드 수집 실패 시 mostPopular 차트 사용 (1 unit짜리라 훨씬 저렴)

할당량 메모 (2026년 기준 문서 확인 필요 - 변경될 수 있음):
  - search.list        : 100 units / 호출
  - videos.list        : 1 unit / 호출
  - commentThreads.list: 1 unit / 호출
  일일 기본 할당량 10,000 units 기준, 키워드 8개 x search 1회 = 800 units로
  전체 예산의 8% 수준만 사용 → 댓글 수집에 여유를 남긴다.
"""
from typing import List, Dict
from src.config import (
    YOUTUBE_API_KEY,
    REGION_CODE,
    MAX_VIDEOS_PER_KEYWORD,
    MAX_COMMENTS_PER_VIDEO,
)


def _get_client():
    from googleapiclient.discovery import build
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def _get_top_comments(youtube, video_id: str) -> List[str]:
    try:
        resp = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=MAX_COMMENTS_PER_VIDEO,
            order="relevance",
            textFormat="plainText",
        ).execute()
        return [
            item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            for item in resp.get("items", [])
        ]
    except Exception as e:
        # 댓글 사용 중지(disabled)된 영상은 흔하므로 조용히 빈 리스트 반환
        print(f"[youtube_collector] 댓글 수집 실패 (video_id={video_id}): {e}")
        return []


def collect_by_keywords(keywords: List[str]) -> List[Dict]:
    """정상 경로: 압축된 키워드로 타겟 검색"""
    youtube = _get_client()
    results = []

    for kw in keywords:
        try:
            search_resp = youtube.search().list(
                part="snippet",
                q=kw,
                type="video",
                order="viewCount",
                regionCode=REGION_CODE,
                relevanceLanguage="ko",
                maxResults=MAX_VIDEOS_PER_KEYWORD,
            ).execute()
        except Exception as e:
            print(f"[youtube_collector] search 실패 (keyword={kw}): {e}")
            continue

        video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
        if not video_ids:
            continue

        stats_resp = youtube.videos().list(
            part="statistics,snippet",
            id=",".join(video_ids),
        ).execute()

        for item in stats_resp.get("items", []):
            results.append({
                "source_keyword": kw,
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "view_count": int(item["statistics"].get("viewCount", 0)),
                "comment_count": int(item["statistics"].get("commentCount", 0)),
                "top_comments": _get_top_comments(youtube, item["id"]),
            })

    return results


def collect_most_popular(max_results: int = 15) -> List[Dict]:
    """폴백 경로: 트렌드 수집 실패 시 사용. 1 unit짜리라 저렴하지만
    '이미 널리 퍼진' 트렌드라 신선도는 낮을 수 있다."""
    youtube = _get_client()
    resp = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        regionCode=REGION_CODE,
        maxResults=max_results,
    ).execute()

    results = []
    for item in resp.get("items", []):
        results.append({
            "source_keyword": "(fallback: mostPopular)",
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "view_count": int(item["statistics"].get("viewCount", 0)),
            "comment_count": int(item["statistics"].get("commentCount", 0)),
            "top_comments": _get_top_comments(youtube, item["id"]),
        })
    return results
