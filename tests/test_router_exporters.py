"""라우터·내보내기·무인증 동작 검증."""
import json
import sqlite3

import pytest

from kci_mcp import config
from kci_mcp.exporters import export
from kci_mcp.models import Article
from kci_mcp.parser import parse_oai_records
from kci_mcp.router import decide_backend
from tests import samples


# ── 라우터 ────────────────────────────────────────────────────────────────────
def test_router_citation_is_rest():
    assert decide_backend(needs="journal_citation", has_key=False)[0] == "rest"
    assert decide_backend(needs="references", has_key=True)[0] == "rest"


def test_router_keyword_depends_on_key():
    assert decide_backend(keyword="학부모", has_key=True)[0] == "rest"
    assert decide_backend(keyword="학부모", has_key=False)[0] == "oai"


def test_router_bulk_is_oai():
    assert decide_backend(has_key=True)[0] == "oai"
    assert decide_backend(has_key=False)[0] == "oai"


# ── 내보내기 (4종 라운드트립) ─────────────────────────────────────────────────
@pytest.fixture
def records():
    arts, _ = parse_oai_records(samples.OAI_LISTRECORDS_KCI)
    return arts


def test_export_all_formats(records, tmp_path):
    paths = export(records, ["json", "csv", "xlsx", "sqlite"], str(tmp_path), "t")
    assert len(paths) == 4
    for p in paths:
        assert (tmp_path / p.split("\\")[-1].split("/")[-1]).exists()
    # json 내용
    data = json.loads((tmp_path / "t.json").read_text(encoding="utf-8"))
    assert data[0]["arti_id"] == "ART001985846"
    assert "raw" in data[0]
    # sqlite 내용
    con = sqlite3.connect(str(tmp_path / "t.sqlite"))
    rows = con.execute("SELECT arti_id, title FROM records").fetchall()
    con.close()
    assert rows[0][0] == "ART001985846"


def test_export_bad_format(records, tmp_path):
    with pytest.raises(ValueError):
        export(records, ["pdf"], str(tmp_path), "t")


def test_article_to_row_joins_lists():
    a = Article(source="oai", arti_id="X", authors=["a", "b"], keywords=["k1", "k2"])
    row = a.to_row()
    assert row["authors"] == "a; b"
    assert row["keywords"] == "k1; k2"
    assert row["source"] == "oai"


# ── 무인증 동작 ────────────────────────────────────────────────────────────────
def test_require_api_key_raises_without_key(monkeypatch):
    monkeypatch.setattr(config, "get_api_key", lambda: None)
    from kci_mcp.client import KciClient
    with pytest.raises(RuntimeError):
        KciClient()


def test_use_os_trust_idempotent():
    # truststore 가 설치돼 있으면 True, 없으면 False — 예외 없이 반환되어야
    assert config.use_os_trust() in (True, False)
