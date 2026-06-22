"""수집 결과(Article)를 xlsx/csv/json/sqlite 로 저장. (scienceon-mcp 패턴 재사용)"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Sequence

from .models import COLUMNS, Article


def _rows(records: Sequence[Article]) -> list[dict]:
    return [r.to_row() for r in records]


def to_json(records: Sequence[Article], path: str) -> None:
    data = [{**r.to_row(), "raw": r.raw} for r in records]
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def to_csv(records: Sequence[Article], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # 엑셀 한글 호환 BOM
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(_rows(records))


def to_xlsx(records: Sequence[Article], path: str) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "records"
    ws.append(COLUMNS)
    for row in _rows(records):
        ws.append([row.get(c, "") for c in COLUMNS])
    wb.save(path)


def to_sqlite(records: Sequence[Article], path: str, *, table: str = "records") -> None:
    con = sqlite3.connect(path)
    try:
        cols = ", ".join(f'"{c}" TEXT' for c in COLUMNS)
        con.execute(f"DROP TABLE IF EXISTS {table}")  # 스냅샷: 재실행 시 누적 방지
        con.execute(f'CREATE TABLE {table} ({cols}, "raw" TEXT)')
        ph = ", ".join(["?"] * (len(COLUMNS) + 1))
        for r in records:
            row = r.to_row()
            con.execute(
                f'INSERT INTO {table} ({", ".join(COLUMNS)}, raw) VALUES ({ph})',
                [row.get(c, "") for c in COLUMNS] + [json.dumps(r.raw, ensure_ascii=False)],
            )
        con.commit()
    finally:
        con.close()


_EXPORTERS = {"json": to_json, "csv": to_csv, "xlsx": to_xlsx, "sqlite": to_sqlite}
_EXT = {"json": ".json", "csv": ".csv", "xlsx": ".xlsx", "sqlite": ".sqlite"}


def export(records: Sequence[Article], formats: Sequence[str], out_dir: str, name: str) -> list[str]:
    """formats 각각으로 out_dir/name.* 저장. 저장된 경로 목록 반환."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for fmt in formats:
        if fmt not in _EXPORTERS:
            raise ValueError(f"지원하지 않는 출력형식: {fmt} (가능: {list(_EXPORTERS)})")
        p = out / f"{name}{_EXT[fmt]}"
        _EXPORTERS[fmt](records, str(p))
        paths.append(str(p))
    return paths
