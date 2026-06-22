"""KCI 수집기 CLI — status/identify/sets/search/detail/references/citation/harvest/collect.

예:
  kci status
  kci identify
  kci harvest --set ARTI --from 2023-01-01 --until 2023-01-31 --contains 학부모 --max 200
  kci search --title 학부모 --rows 20            # 인증키 필요
  kci collect --config config/search.example.yaml
"""
from __future__ import annotations

import argparse
import sys

from .config import get_api_key
from .oai_client import KciOaiClient
from .parser import OaiError


def cmd_status(args) -> int:
    print("KCI_API_KEY:", "설정됨" if get_api_key() else "없음(OAI만 사용 가능)")
    try:
        info = KciOaiClient().identify()
        print("OAI OK:", info.get("repositoryName"), "| earliest:", info.get("earliestDatestamp"))
        return 0
    except Exception as e:  # noqa: BLE001
        print("OAI FAIL:", e)
        return 1


def cmd_identify(args) -> int:
    for k, v in KciOaiClient().identify().items():
        print(f"{k:18}: {v}")
    return 0


def cmd_sets(args) -> int:
    for s in KciOaiClient().list_sets():
        print(f"{s['setSpec']:12} {s['setName']}")
    return 0


def cmd_harvest(args) -> int:
    try:
        recs = KciOaiClient(throttle=args.throttle).list_records(
            set_spec=args.set, metadata_prefix=args.prefix,
            date_from=getattr(args, "from"), date_until=args.until,
            max_records=args.max, contains=args.contains)
    except OaiError as e:
        print("오류:", e)
        return 1
    for r in recs[:args.show]:
        print(f"[{r.pub_year}] {r.title}  / {'; '.join(r.authors)}  ({r.arti_id})")
    print(f"\n수확 {len(recs)}건 (표시 {min(len(recs), args.show)})")
    if args.out:
        from .exporters import export
        paths = export(recs, args.formats, args.out, args.name or (args.set or "kci"))
        for p in paths:
            print("저장:", p)
    return 0


def cmd_search(args) -> int:
    if get_api_key() is None:
        print("KCI_API_KEY 미설정 — REST 검색 불가. 'kci harvest --contains' 사용을 권장.")
        return 2
    from .client import KciClient, KciError
    filters = {k: v for k, v in {"author": args.author, "journal": args.journal,
                                 "keyword": args.keyword}.items() if v}
    try:
        recs = KciClient().search(args.title, max_records=max(args.rows, 100),
                                  display=100, **filters)
    except KciError as e:
        print("오류:", e)
        return 1
    for r in recs[:args.rows]:
        print(f"[{r.pub_year}] {r.title}  / {'; '.join(r.authors)}  ({r.arti_id})")
    print(f"\n표시 {min(len(recs), args.rows)} / 합집합 {len(recs)}건")
    return 0


def cmd_detail(args) -> int:
    if get_api_key() is None:
        print("KCI_API_KEY 미설정 — REST 상세조회 불가.")
        return 2
    from .client import KciClient, KciError
    try:
        r = KciClient().detail(args.id)
    except KciError as e:
        print("오류:", e)
        return 1
    if not r:
        print("결과 없음")
        return 1
    for k, v in r.to_row().items():
        print(f"{k:14}: {v}")
    return 0


def cmd_collect(args) -> int:
    import yaml

    from .exporters import export
    from .router import decide_backend
    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    title = cfg.get("title")
    oai = cfg.get("oai", {})
    forced = cfg.get("backend", "auto")
    backend, reason = decide_backend(keyword=title)
    if forced in ("rest", "oai"):
        backend, reason = forced, f"설정 강제: {forced}"
    print(f"backend={backend} ({reason})")
    max_records = int(cfg.get("max_records", 2000))
    try:
        if backend == "rest":
            from .client import KciClient, KciError
            try:
                recs = KciClient(throttle=float(cfg.get("throttle_sec", 0.5))).search(
                    title, max_records=max_records, display=100)
            except KciError as e:
                print("오류:", e)
                return 1
        else:
            subs = oai.get("contains") or ([title] if title else None)
            recs = KciOaiClient(throttle=float(cfg.get("throttle_sec", 0.5))).list_records(
                set_spec=oai.get("set", "ARTI"), metadata_prefix=oai.get("metadata_prefix", "oai_kci"),
                date_from=oai.get("date_from"), date_until=oai.get("date_until"),
                max_records=max_records, contains=subs)
    except OaiError as e:
        print("오류:", e)
        return 1
    out = cfg.get("output", {})
    project = cfg.get("project", "kci_collect")
    paths = export(recs, out.get("formats", ["xlsx", "csv", "json"]),
                   out.get("dir", f"output/{project}"), project)
    print(f"수집 {len(recs)}건 저장:")
    for p in paths:
        print("  -", p)
    return 0


def main() -> None:
    p = argparse.ArgumentParser(prog="kci", description="KCI 문헌 메타데이터 수집기 (REST + OAI-PMH)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="연결 점검(OAI Identify + 키 보유)").set_defaults(func=cmd_status)
    sub.add_parser("identify", help="OAI 저장소 정보").set_defaults(func=cmd_identify)
    sub.add_parser("sets", help="OAI 세트 목록").set_defaults(func=cmd_sets)

    h = sub.add_parser("harvest", help="[OAI·무인증] 세트+날짜범위 대량 수확")
    h.add_argument("--set", default="ARTI", help="ARTI/ARTI_CONF/JOUR")
    h.add_argument("--prefix", default="oai_kci", help="oai_kci/oai_dc")
    h.add_argument("--from", dest="from", help="시작일 YYYY-MM-DD")
    h.add_argument("--until", help="종료일 YYYY-MM-DD")
    h.add_argument("--contains", action="append", help="포함 필터(여러 번 가능)")
    h.add_argument("--max", type=int, default=200)
    h.add_argument("--show", type=int, default=20)
    h.add_argument("--throttle", type=float, default=0.5)
    h.add_argument("--out", help="저장 디렉터리(지정 시 파일 저장)")
    h.add_argument("--name", help="파일명 베이스")
    h.add_argument("--formats", nargs="+", default=["xlsx", "csv", "json"])
    h.set_defaults(func=cmd_harvest)

    s = sub.add_parser("search", help="[REST] 논문 검색(인증키 필요)")
    s.add_argument("--title", required=True)
    s.add_argument("--author")
    s.add_argument("--journal")
    s.add_argument("--keyword")
    s.add_argument("--rows", type=int, default=20)
    s.set_defaults(func=cmd_search)

    d = sub.add_parser("detail", help="[REST] 상세(Control Number)")
    d.add_argument("--id", required=True)
    d.set_defaults(func=cmd_detail)

    c = sub.add_parser("collect", help="설정 기반 혼용 수집(auto/rest/oai)")
    c.add_argument("--config", required=True)
    c.set_defaults(func=cmd_collect)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
