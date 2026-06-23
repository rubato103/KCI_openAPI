"""KCI MCP 서버 (FastMCP) — REST + OAI-PMH 혼용 도구.

- 인증키(KCI_API_KEY) 있으면 REST 도구 동작. 없어도 OAI 수확 도구는 동작(무인증).
- kci_collect 는 요청 성격·키 유무로 백엔드를 자동 선택(router). 설계: docs/ARCHITECTURE.md
"""
from __future__ import annotations

import functools
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import get_api_key
from .oai_client import KciOaiClient
from .parser import OaiError
from .router import decide_backend

mcp = FastMCP("kci")


def _safe(fn):
    """도구는 **항상 JSON 직렬화 가능한 dict** 를 반환 — 어떤 예외도 도구 밖으로 누수 금지.

    (네트워크/SSL/HTTP/파싱 예외가 MCP 프로토콜 밖으로 새어 클라이언트가 깨지는 것을 방지.
    _call 단계에서 인증키 포함 URL 은 이미 제거되므로 메시지에 키가 노출되지 않는다.)
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            return {"error": f"{type(e).__name__}: {e}"}
    return wrapper


# 도구 안전성 힌트(MCP annotations) — 디렉터리 심사·클라이언트 표시에 사용.
# 전부 외부 API 조회(openWorld). collect 만 파일 생성(쓰기, 비파괴).
_READ = {"readOnlyHint": True, "openWorldHint": True}
_WRITE = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}


# ── 상태 ──────────────────────────────────────────────────────────────────────
@mcp.tool(annotations=_READ)
@_safe
def kci_status() -> dict:
    """연결 점검 — OAI(무인증) Identify + REST 인증키 보유 여부."""
    info: dict = {"has_api_key": get_api_key() is not None}
    try:
        info["oai"] = {"ok": True, **KciOaiClient().identify()}
    except Exception as e:  # noqa: BLE001
        info["oai"] = {"ok": False, "error": str(e)}
    if not info["has_api_key"]:
        info["rest"] = {"ok": False, "note": "KCI_API_KEY 미설정 — REST 도구 비활성(OAI는 사용 가능)"}
    else:
        info["rest"] = {"ok": True, "note": "인증키 보유 — REST 도구 사용 가능(라이브 미검증)"}
    return info


# ── REST ─────────────────────────────────────────────────────────────────────
@mcp.tool(annotations=_READ)
@_safe
def kci_search(title: str, author: str | None = None, journal: str | None = None,
               keyword: str | None = None, abstract: str | None = None, doi: str | None = None,
               date_from: str | None = None, date_to: str | None = None,
               rows: int = 20) -> dict:
    """[REST] 논문 검색 — title 필수 + 선택 필터. 인증키 필요.

    date_from/date_to: 발행연월 YYYYMM. rows: 반환 건수(최대 100).
    인증키가 없으면 kci_harvest(OAI 무인증) 사용을 안내한다.
    """
    if get_api_key() is None:
        return {"error": "KCI_API_KEY 미설정 — REST 검색 불가. 인증키 없이 수집하려면 kci_harvest 사용.",
                "hint": "kci_harvest 로 OAI(무인증) 날짜범위 수확 후 contains 로 필터하세요.",
                "suggested_contains": [title]}
    from .client import KciClient, KciError
    filters = {k: v for k, v in {
        "author": author, "journal": journal, "keyword": keyword,
        "abstract": abstract, "doi": doi, "dateFrom": date_from, "dateTo": date_to,
    }.items() if v}
    try:
        recs = KciClient().search(title, max_records=min(rows, 100), display=min(rows, 100), **filters)
    except KciError as e:
        return {"error": str(e)}
    recs = recs[:rows]
    return {"count": len(recs), "records": [r.to_row() for r in recs]}


@mcp.tool(annotations=_READ)
@_safe
def kci_detail(arti_id: str) -> dict:
    """[REST] Control Number(ART…)로 논문 상세·초록·키워드·저자 조회. 인증키 필요."""
    if get_api_key() is None:
        return {"error": "KCI_API_KEY 미설정 — REST 상세조회 불가."}
    from .client import KciClient, KciError
    try:
        r = KciClient().detail(arti_id)
    except KciError as e:
        return {"error": str(e)}
    return r.to_row() if r else {"error": "결과 없음"}


@mcp.tool(annotations=_READ)
@_safe
def kci_references(title: str, author: str | None = None, pub_year: str | None = None,
                  rows: int = 50) -> dict:
    """[REST] 제목 검색어에 매칭된 논문들의 참고문헌 원형 수집. 인증키 필요."""
    if get_api_key() is None:
        return {"error": "KCI_API_KEY 미설정 — referenceSearch 는 REST 전용(OAI 미제공)."}
    from .client import KciClient, KciError
    filters = {k: v for k, v in {"author": author, "pubiYr": pub_year}.items() if v}
    try:
        refs = KciClient().references(title, max_records=rows, **filters)
    except KciError as e:
        return {"error": str(e)}
    return {"count": len(refs), "references": refs}


@mcp.tool(annotations=_READ)
@_safe
def kci_journal_citation(year: int | None = None, years: int = 2, journal_id: str | None = None,
                        rows: int = 50) -> dict:
    """[REST] 저널 인용지수 — year(+years 2~5)로 목록 / journal_id 로 상세(등재이력·연도별 IF). 인증키 필요."""
    if get_api_key() is None:
        return {"error": "KCI_API_KEY 미설정 — 인용지수는 REST 전용(OAI 미제공)."}
    from .client import KciClient, KciError
    try:
        c = KciClient()
        if journal_id:
            d = c.citation_detail(journal_id)
            return d or {"error": "결과 없음"}
        if year is None:
            return {"error": "year(기준년도) 또는 journal_id 중 하나는 필요합니다."}
        rows_ = c.citation(year, years=years, max_records=rows)
    except KciError as e:
        return {"error": str(e)}
    return {"count": len(rows_), "citations": rows_}


# ── OAI-PMH (무인증) ───────────────────────────────────────────────────────────
@mcp.tool(annotations=_READ)
@_safe
def kci_harvest(set_spec: str = "ARTI", date_from: str | None = None, date_until: str | None = None,
                metadata_prefix: str = "oai_kci", contains: list[str] | None = None,
                max_records: int = 200) -> dict:
    """[OAI-PMH·무인증] 세트+날짜범위 대량 수확. 인증키 불필요.

    set_spec: ARTI(논문)/ARTI_CONF(학술대회)/JOUR(학술지)
    date_from/date_until: YYYY-MM-DD. metadata_prefix: oai_kci(상세)/oai_dc(간략).
    contains: 제목/초록/키워드 등에 이 문자열(들) 포함분만(키워드 검색 대용 로컬 필터).
    """
    try:
        recs = KciOaiClient().list_records(
            set_spec=set_spec, metadata_prefix=metadata_prefix,
            date_from=date_from, date_until=date_until,
            max_records=max_records, contains=contains)
    except OaiError as e:
        return {"error": str(e)}
    return {"count": len(recs), "records": [r.to_row() for r in recs]}


# ── 혼용 수집 + 내보내기 ─────────────────────────────────────────────────────────
@mcp.tool(annotations=_WRITE)
@_safe
def kci_collect(title: str | None = None, terms: list[str] | None = None, set_spec: str = "ARTI",
                year_from: int | None = None, year_to: int | None = None,
                date_from: str | None = None, date_until: str | None = None,
                contains: list[str] | None = None, formats: list[str] | None = None,
                max_records: int = 500, out_dir: str | None = None, name: str | None = None) -> dict:
    """[혼용] 요청 성격·키 유무로 REST↔OAI 자동 선택 후 수집 → 파일 저장.

    - terms/title 있고 인증키 보유 → REST 변형어 합집합 검색(year_from/to·contains 적용)
    - terms/title 있고 키 없음 → OAI 수확(date_from/until) + terms/contains 로컬 필터
    - terms/title 없음 → OAI 세트/날짜범위 전수 수확
    out_dir 미지정 시 홈의 kci-output/. OAI 날짜는 YYYY-MM-DD, REST 연도는 정수.
    """
    from .exporters import export
    kws = [t for t in (terms or ([title] if title else [])) if t]
    backend, reason = decide_backend(keyword=(kws[0] if kws else None))
    try:
        if backend == "rest":
            from .client import KciClient, KciError
            try:
                recs = KciClient().search_terms(kws, year_from=year_from, year_to=year_to,
                                                max_records=max_records, contains=contains)
            except KciError as e:
                return {"error": str(e), "backend": backend, "reason": reason}
        else:
            subs = contains or (kws or None)
            recs = KciOaiClient().list_records(
                set_spec=set_spec, metadata_prefix="oai_kci",
                date_from=date_from, date_until=date_until,
                max_records=max_records, contains=subs)
    except OaiError as e:
        return {"error": str(e), "backend": backend, "reason": reason}
    fmts = formats or ["xlsx", "csv", "json"]
    nm = (name or f"kci_{(kws[0] if kws else set_spec)}").replace(" ", "_")[:60]
    base = out_dir or str(Path.home() / "kci-output")
    paths = export(recs, fmts, base, nm)
    return {"count": len(recs), "backend": backend, "reason": reason, "files": paths}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
