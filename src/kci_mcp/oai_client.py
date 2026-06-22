"""KCI OAI-PMH 클라이언트 — **무인증** 대량 수확.

verb: Identify · ListSets · ListIdentifiers · ListMetadataFormats · ListRecords · GetRecord
ListRecords 는 resumptionToken 으로 100건씩 페이징(토큰 재요청 시 다른 파라미터 동반 금지 = OAI 표준).
규격: docs/KCI_OAI_PMH_GUIDE.md
"""
from __future__ import annotations

import time

import requests

from .config import OAI_URL, use_os_trust
from .models import Article
from .parser import (
    OaiError,
    parse_oai_formats,
    parse_oai_identifiers,
    parse_oai_identify,
    parse_oai_records,
    parse_oai_sets,
)


def _contains_any(a: Article, subs: list[str]) -> bool:
    """하위호환 래퍼 — 실제 로직은 Article.matches (REST/OAI 공통)."""
    return a.matches(subs)


class KciOaiClient:
    def __init__(self, *, throttle: float = 0.5, timeout: int = 30):
        use_os_trust()  # 교육망/사내망 SSL 인터셉션 CA를 OS 저장소로 신뢰(검증 유지)
        self.throttle = throttle
        self.timeout = timeout

    def _call(self, params: dict) -> str:
        for attempt in range(3):
            r = requests.get(OAI_URL, params=params, timeout=self.timeout)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(1.5 * (2 ** attempt))  # 지수 백오프
                continue
            break
        if r.status_code == 429:
            raise OaiError("429", "요청 한도 초과 — throttle 상향 또는 잠시 후 재시도.")
        r.raise_for_status()
        return r.text

    # ── 단순 verb ────────────────────────────────────────────────────────────
    def identify(self) -> dict:
        return parse_oai_identify(self._call({"verb": "Identify"}))

    def list_sets(self) -> list[dict]:
        return parse_oai_sets(self._call({"verb": "ListSets"}))

    def list_metadata_formats(self) -> list[dict]:
        return parse_oai_formats(self._call({"verb": "ListMetadataFormats"}))

    def list_identifiers(self, *, metadata_prefix: str = "oai_dc", date_from: str | None = None,
                         date_until: str | None = None, max_records: int = 1000) -> list[dict]:
        out: list[dict] = []
        params: dict = {"verb": "ListIdentifiers", "metadataPrefix": metadata_prefix}
        if date_from:
            params["from"] = date_from
        if date_until:
            params["until"] = date_until
        while len(out) < max_records:
            headers, token = parse_oai_identifiers(self._call(params))
            out.extend(headers)
            if not token:
                break
            params = {"verb": "ListIdentifiers", "resumptionToken": token}
            time.sleep(self.throttle)
        return out[:max_records]

    # ── 레코드 수확 ───────────────────────────────────────────────────────────
    def get_record(self, identifier: str, *, metadata_prefix: str = "oai_kci") -> Article | None:
        text = self._call({"verb": "GetRecord", "identifier": identifier,
                           "metadataPrefix": metadata_prefix})
        arts, _ = parse_oai_records(text)
        return arts[0] if arts else None

    def list_records(self, *, set_spec: str | None = "ARTI", metadata_prefix: str = "oai_kci",
                     date_from: str | None = None, date_until: str | None = None,
                     max_records: int = 1000, contains: list[str] | None = None,
                     max_pages: int = 100000) -> list[Article]:
        """세트+날짜범위 대량 수확. contains 지정 시 로컬 부분일치 필터(키워드 검색 대용)."""
        out: list[Article] = []
        seen: set = set()
        params: dict = {"verb": "ListRecords", "metadataPrefix": metadata_prefix}
        if set_spec:
            params["set"] = set_spec
        if date_from:
            params["from"] = date_from
        if date_until:
            params["until"] = date_until
        pages = 0
        while len(out) < max_records and pages < max_pages:
            arts, token = parse_oai_records(self._call(params))
            pages += 1
            for a in arts:
                if contains and not _contains_any(a, contains):
                    continue
                key = a.dedup_key()
                if key in seen:
                    continue
                seen.add(key)
                out.append(a)
                if len(out) >= max_records:
                    break
            if not token:
                break
            params = {"verb": "ListRecords", "resumptionToken": token}
            time.sleep(self.throttle)
        return out[:max_records]

    harvest = list_records  # 별칭
