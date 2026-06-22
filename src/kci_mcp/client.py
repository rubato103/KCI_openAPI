"""KCI REST Open API 클라이언트 — 검색/상세/참고문헌/인용지수.

호출: openApiSearch.kci?apiCode=<…>&key=<인증키>&…  (GET, 응답 XML/UTF-8)
규격: docs/KCI_API_GUIDE.md  ⚠️ 라이브 미검증(키 발급 후 확정).
"""
from __future__ import annotations

import time

import requests

from .config import REST_API_URL, require_api_key, use_os_trust
from .models import Article
from .parser import (
    ParseError,
    parse_rest_articles,
    parse_rest_citation,
    parse_rest_references,
)


class KciError(RuntimeError):
    pass


class KciClient:
    def __init__(self, api_key: str | None = None, *, throttle: float = 0.5, timeout: int = 20):
        use_os_trust()  # 교육망/사내망 SSL 인터셉션 CA를 OS 저장소로 신뢰(검증 유지)
        self.api_key = api_key or require_api_key()
        self.throttle = throttle
        self.timeout = timeout

    def _call(self, api_code: str, params: dict) -> str:
        base = {"apiCode": api_code, "key": self.api_key}
        base.update({k: v for k, v in params.items() if v not in (None, "")})
        for attempt in range(3):
            r = requests.get(REST_API_URL, params=base, timeout=self.timeout)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(1.5 * (2 ** attempt))
                continue
            break
        if r.status_code == 429:
            raise KciError("요청 한도 초과(429) — throttle 상향 또는 잠시 후 재시도.")
        r.raise_for_status()
        return r.text

    # ── articleSearch ─────────────────────────────────────────────────────────
    def search_page(self, title: str, *, page: int = 1, display: int = 100,
                    **filters) -> tuple[int, list[Article]]:
        params = {"title": title, "page": page, "displayCount": min(display, 100)}
        params.update(filters)  # author/journal/keyword/abstract/doi/dateFrom… sortNm/sortDir
        try:
            return parse_rest_articles(self._call("articleSearch", params))
        except ParseError as e:
            raise KciError(str(e)) from e

    def search(self, title: str, *, max_records: int = 1000, display: int = 100,
               **filters) -> list[Article]:
        out: list[Article] = []
        seen: set = set()
        page = 1
        while len(out) < max_records and page <= 1000:
            total, arts = self.search_page(title, page=page, display=display, **filters)
            if not arts:
                break
            before = len(out)
            for a in arts:
                key = a.dedup_key()
                if key in seen:
                    continue
                seen.add(key)
                out.append(a)
            if len(out) == before:
                break
            if total and page * display >= total:
                break
            page += 1
            time.sleep(self.throttle)
        return out[:max_records]

    # ── articleDetail ─────────────────────────────────────────────────────────
    def detail(self, arti_id: str) -> Article | None:
        try:
            _, arts = parse_rest_articles(self._call("articleDetail", {"id": arti_id}))
        except ParseError as e:
            raise KciError(str(e)) from e
        return arts[0] if arts else None

    # ── referenceSearch ───────────────────────────────────────────────────────
    def references(self, title: str, *, max_records: int = 100, display: int = 100,
                   **filters) -> list[dict]:
        params = {"title": title, "displayCount": min(display, 100)}
        params.update(filters)  # author/institution/pubiYr/sortNm/sortDir
        try:
            _, refs = parse_rest_references(self._call("referenceSearch", params))
        except ParseError as e:
            raise KciError(str(e)) from e
        return refs[:max_records]

    # ── citation / citationDetail ─────────────────────────────────────────────
    def citation(self, year: int, *, years: int = 2, max_records: int = 100,
                 display: int = 100, **filters) -> list[dict]:
        years = max(2, min(years, 5))
        params = {"year": year, "years": years, "displayCount": min(display, 100)}
        params.update(filters)  # journal/doi/institution/modDate…/sortNm/sortDir
        try:
            _, rows = parse_rest_citation(self._call("citation", params))
        except ParseError as e:
            raise KciError(str(e)) from e
        return rows[:max_records]

    def citation_detail(self, journal_id: str) -> dict | None:
        try:
            _, rows = parse_rest_citation(self._call("citationDetail", {"id": journal_id}))
        except ParseError as e:
            raise KciError(str(e)) from e
        return rows[0] if rows else None
