"""혼용 라우팅 — 요청 성격 + 인증키 유무로 백엔드 선택.

설계 근거·표: docs/ARCHITECTURE.md §3
"""
from __future__ import annotations

from .config import get_api_key


def decide_backend(*, needs: str | None = None, keyword: str | None = None,
                   has_key: bool | None = None) -> tuple[str, str]:
    """(backend, reason) 반환. backend ∈ {'rest','oai'}.

    needs : 'journal_citation' | 'references' | None
    keyword : 주제어(있으면 검색형). 없으면 세트/날짜 전수 수확형.
    """
    if has_key is None:
        has_key = get_api_key() is not None

    if needs in ("journal_citation", "references"):
        return "rest", f"{needs} 은 REST 전용(OAI 미제공)"
    if keyword:
        if has_key:
            return "rest", "키워드 검색 + 인증키 보유 → REST 정밀 검색"
        return "oai", "키워드 검색이지만 인증키 없음 → OAI 수확 후 로컬 필터"
    return "oai", "세트/날짜범위 전수·증분 → OAI 무인증 수확"
