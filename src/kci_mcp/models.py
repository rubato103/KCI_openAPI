"""정규화된 메타데이터 스키마 — REST/OAI 공통 통합 레코드.

REST `articleSearch`/`articleDetail` 와 OAI `oai_kci`/`oai_dc` 가 거의 동일한 서지를 주므로
하나의 `Article` 로 흡수한다(`source` 로 출처 태깅, 원본은 `raw` 보존).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 표 출력(csv/xlsx/sqlite) 시 컬럼 순서
COLUMNS = [
    "source", "arti_id", "title", "title_en", "authors",
    "journal", "issn", "publisher", "pub_year", "pub_mon", "volume", "issue",
    "categories", "abstract", "abstract_en", "keywords",
    "citation_count", "doi", "uci", "url",
]


@dataclass
class Article:
    """REST/OAI 공통 정규화 논문 레코드."""

    source: str                                  # 'rest' | 'oai'
    arti_id: str = ""                            # KCI 논문 제어번호 (ART…)
    title: str = ""                              # 국문(원어) 제목
    title_en: str = ""                           # 영문 제목
    authors: list[str] = field(default_factory=list)   # "이름" 또는 "이름(소속)"
    journal: str = ""
    issn: str = ""
    publisher: str = ""
    pub_year: str = ""
    pub_mon: str = ""
    volume: str = ""
    issue: str = ""
    categories: str = ""                         # 연구분야
    abstract: str = ""                           # 국문(원어) 초록
    abstract_en: str = ""                        # 영문 초록
    keywords: list[str] = field(default_factory=list)
    citation_count: str = ""
    doi: str = ""
    uci: str = ""
    url: str = ""
    raw: dict[str, Any] = field(default_factory=dict)   # 원본 필드 보존

    def to_row(self, *, list_sep: str = "; ") -> dict[str, Any]:
        """평탄화된 표 한 행(dict). 리스트 필드는 구분자로 join."""
        row: dict[str, Any] = {}
        for col in COLUMNS:
            val = getattr(self, col)
            row[col] = list_sep.join(val) if isinstance(val, list) else val
        return row

    def dedup_key(self):
        return self.arti_id or self.doi or (self.title, self.pub_year)

    def haystack(self) -> str:
        """부분일치 필터용 전체 텍스트(소문자)."""
        parts = [self.title, self.title_en, self.abstract, self.abstract_en, self.categories,
                 "; ".join(self.authors), "; ".join(self.keywords)]
        parts += [v for v in self.raw.values() if isinstance(v, str)]
        return "\n".join(parts).lower()

    def matches(self, subs) -> bool:
        """subs(문자열 또는 목록) 중 하나라도 부분일치하면 True (대소문자 무시)."""
        if isinstance(subs, str):
            subs = [subs]
        hay = self.haystack()
        return any(s.lower() in hay for s in subs)
