"""OAI-PMH 응답 파서 검증 — 공식 가이드 예제 XML 기반(오프라인)."""
import pytest

from kci_mcp.parser import OaiError, parse_oai_records
from tests import samples


def test_oai_kci_record():
    arts, token = parse_oai_records(samples.OAI_LISTRECORDS_KCI)
    assert token == "2023-01-01:2023-01-31:100:1014"
    assert len(arts) == 1
    a = arts[0]
    assert a.source == "oai"
    assert a.arti_id == "ART001985846"
    assert a.title.startswith("1930년대 기생")
    assert a.title_en.startswith("A Study")
    assert a.journal == "대중서사연구"
    assert a.issn == "1738-3188"
    assert a.pub_year == "2015" and a.pub_mon == "04"
    assert a.volume == "21" and a.issue == "1"
    # author-name(이름+소속 분리) 우선
    assert a.authors == ["백현미(전남대학교)"]
    assert a.abstract.startswith("연애와 여성")
    assert a.abstract_en.startswith("A study")
    assert a.doi.endswith("2015.21.1.008")
    assert a.uci.startswith("G704")
    # 헤더 보존
    assert a.raw["oai_identifier"] == "oai:kci.go.kr:ARTI/914"
    assert a.raw["setSpec"] == "ARTI"


def test_oai_dc_record():
    arts, token = parse_oai_records(samples.OAI_LISTRECORDS_DC)
    assert token is None
    a = arts[0]
    assert a.arti_id == "ART001985846"
    assert a.title.startswith("1930년대 기생")
    assert a.title_en.startswith("A Study")
    assert a.authors == ["백현미(전남대학교)"]   # creator 세미콜론 분해
    assert a.categories == "학제간연구"
    assert a.journal == "대중서사연구"            # journalInfo identifier 앞부분
    assert a.issn == "1738-3188"
    assert a.abstract.startswith("연애와 여성")
    assert a.pub_year == "2015" and a.pub_mon == "04"   # date YYYY-MM 분해
    assert a.doi.endswith("2015.21.1.08")


def test_oai_error_raises():
    with pytest.raises(OaiError):
        parse_oai_records(samples.OAI_ERROR)
