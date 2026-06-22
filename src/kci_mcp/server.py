"""KCI MCP 서버 (FastMCP) — REST + OAI-PMH 혼용 도구.

- 인증키(KCI_API_KEY) 있으면 REST 도구 동작. 없어도 OAI 수확 도구는 동작(무인증).
- kci_collect 는 요청 성격·키 유무로 백엔드를 자동 선택(router). 설계: docs/ARCHITECTURE.md
"""
from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import get_api_key
from .oai_client import KciOaiClient
from .parser import OaiError
from .router import decide_backend

mcp = FastMCP("kci")


# ── 상태 ──────────────────────────────────────────────────────────────────────
@mcp.tool()
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
@mcp.tool()
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
                "hint": "kci_harvest(set_spec='ARTI', date_from='2013-01-01', contains=['" + title + "'])"}
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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
@mcp.tool()
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
@mcp.tool()
def kci_collect(title: str | None = None, set_spec: str = "ARTI",
                date_from: str | None = None, date_until: str | None = None,
                contains: list[str] | None = None, formats: list[str] | None = None,
                max_records: int = 500, out_dir: str | None = None, name: str | None = None) -> dict:
    """[혼용] 요청 성격·키 유무로 REST↔OAI 자동 선택 후 수집 → 파일 저장.

    - title 있고 인증키 보유 → REST 검색
    - title 있고 키 없음 → OAI 수확(날짜범위) + title 로컬 필터
    - title 없음 → OAI 세트/날짜범위 전수 수확
    OAI 경로에서 date_from/until(YYYY-MM-DD) 권장. out_dir 미지정 시 홈의 kci-output/.
    """
    from .exporters import export
    backend, reason = decide_backend(keyword=title)
    used = backend
    try:
        if backend == "rest":
            from .client import KciClient, KciError
            try:
                recs = KciClient().search(title, max_records=max_records, display=100)
            except KciError as e:
                return {"error": str(e), "backend": backend, "reason": reason}
        else:
            subs = contains or ([title] if title else None)
            recs = KciOaiClient().list_records(
                set_spec=set_spec, metadata_prefix="oai_kci",
                date_from=date_from, date_until=date_until,
                max_records=max_records, contains=subs)
    except OaiError as e:
        return {"error": str(e), "backend": used, "reason": reason}
    fmts = formats or ["xlsx", "csv", "json"]
    nm = (name or f"kci_{title or set_spec}").replace(" ", "_")[:60]
    base = out_dir or str(Path.home() / "kci-output")
    paths = export(recs, fmts, base, nm)
    return {"count": len(recs), "backend": used, "reason": reason, "files": paths}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
