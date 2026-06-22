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
    # 라이브 검증(2026-06-22): `title` 은 제목검색(토큰화, 띄어쓰기 무관). `keyword` 는 **단독 검색 가능**
    # (title 없이도 동작) — 제목엔 없고 키워드에만 있는 논문 회수에 유효. `abstract` 단독은 0건.
    def search_page(self, value: str, *, field: str = "title", page: int = 1, display: int = 100,
                    **filters) -> tuple[int, list[Article]]:
        params = {field: value, "page": page, "displayCount": min(display, 100)}
        params.update(filters)  # author/journal/doi/dateFrom… sortNm/sortDir
        try:
            return parse_rest_articles(self._call("articleSearch", params))
        except ParseError as e:
            raise KciError(str(e)) from e

    def search(self, value: str, *, field: str = "title", max_records: int = 1000,
               display: int = 100, **filters) -> list[Article]:
        out: list[Article] = []
        seen: set = set()
        page = 1
        while len(out) < max_records and page <= 1000:
            total, arts = self.search_page(value, field=field, page=page, display=display, **filters)
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

    def search_terms(self, terms, *, fields=("title", "keyword"),
                     year_from: int | None = None, year_to: int | None = None,
                     max_records: int = 3000, display: int = 100, contains=None,
                     **filters) -> list[Article]:
        """여러 변형어를 **각 필드(기본 title+keyword)로 개별 검색**해 arti_id/DOI 합집합(중복제거).

        KCI는 필드 내 OR 연산자가 없으므로 변형어·필드별 개별검색 합집합이 정석.
        title=제목검색, keyword=키워드검색(단독 가능). year_from/to→dateFrom/To(YYYYMM).
        contains→결과 부분일치 후처리 필터.
        """
        terms = [t.strip() for t in (terms or []) if t and t.strip()]
        if year_from:
            filters["dateFrom"] = f"{year_from}01"
        if year_to:
            filters["dateTo"] = f"{year_to}12"
        out: list[Article] = []
        seen: set = set()
        for term in terms:
            for field in fields:
                for a in self.search(term, field=field, max_records=max_records,
                                     display=display, **filters):
                    k = a.dedup_key()
                    if k in seen:
                        continue
                    seen.add(k)
                    out.append(a)
                if len(out) >= max_records:
                    break
            if len(out) >= max_records:
                break
        out = out[:max_records]
        if contains:
            subs = [contains] if isinstance(contains, str) else list(contains)
            out = [a for a in out if a.matches(subs)]
        return out

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
