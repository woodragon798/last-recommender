"""
History/State Layer
- 별도 DB 없이 저장소 안의 JSON 파일 하나로 이력을 관리한다.
- 최근 N일간 추천된 아이템명을 기록해 Reasoning Layer에 "제외 목록"으로 전달한다.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict

from src.config import HISTORY_FILE, HISTORY_RETENTION_DAYS

KST = timezone(timedelta(hours=9))


def load_history() -> List[Dict]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print("[history_manager] history.json 파싱 실패. 빈 이력으로 시작합니다.")
        return []


def get_recent_item_names(history: List[Dict]) -> List[str]:
    """최근 HISTORY_RETENTION_DAYS일 내 추천된 아이템명만 뽑아 중복 제외 목록으로 사용"""
    cutoff = datetime.now(KST) - timedelta(days=HISTORY_RETENTION_DAYS)
    names = []
    for entry in history:
        try:
            entry_date = datetime.fromisoformat(entry["date"])
        except (KeyError, ValueError):
            continue
        if entry_date >= cutoff:
            names.extend(item["name"] for item in entry.get("items", []))
    return names


def append_today(history: List[Dict], items: List[Dict], data_source_status: str) -> List[Dict]:
    """오늘자 추천 결과를 이력에 추가하고, 오래된 항목은 정리한다."""
    today_str = datetime.now(KST).isoformat()
    history.append({
        "date": today_str,
        "data_source_status": data_source_status,  # "ok" | "fallback"
        "items": [{"name": item["name"]} for item in items],
    })

    cutoff = datetime.now(KST) - timedelta(days=HISTORY_RETENTION_DAYS)
    pruned = []
    for entry in history:
        try:
            entry_date = datetime.fromisoformat(entry["date"])
        except (KeyError, ValueError):
            continue
        if entry_date >= cutoff:
            pruned.append(entry)
    return pruned


def save_history(history: List[Dict]) -> None:
    os.makedirs(os.path.dirname(HISTORY_FILE) or ".", exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
