"""REST 응답 파서 검증 — 공식 가이드 예제 XML 기반(오프라인)."""
import pytest

from kci_mcp.parser import (
    ParseError,
    parse_rest_articles,
    parse_rest_citation,
    parse_rest_references,
)
from tests import samples


def test_article_search():
    total, arts = parse_rest_articles(samples.REST_ARTICLE_SEARCH)
    assert total == 3779
    assert len(arts) == 1
    a = arts[0]
    assert a.source == "rest"
    assert a.arti_id == "ART001143784"
    assert a.title.startswith("초등학교 컴퓨터")
    assert a.title_en.startswith("An Analysis")
    assert a.journal == "컴퓨터교육학회논문지"
    assert a.publisher == "한국컴퓨터교육학회"
    assert a.pub_year == "2004" and a.pub_mon == "09"
    assert a.volume == "8" and a.issue == "3"
    assert a.categories == "컴퓨터교육"
    assert len(a.authors) == 3
    assert a.authors[0] == "김갑수(서울교육대학교)"
    assert "컴퓨터 용어를 알아야" in a.abstract
    assert a.abstract_en.startswith("We must know")
    assert a.citation_count == "4"   # 본문값 우선


def test_article_detail():
    total, arts = parse_rest_articles(samples.REST_ARTICLE_DETAIL)
    assert total == 1 and len(arts) == 1
    a = arts[0]
    assert a.arti_id == "ART002358582"
    assert a.issn == "2383-5281"
    assert a.title == "컴퓨터 학습을 통한 디지털 에이징"
    assert a.categories == "공학 > 컴퓨터학"         # &gt; 디코드
    # articleDetail 의 중첩 저자(name/institution) → "이름(소속)"
    assert a.authors == ["김정진(백석대학교)"]
    assert a.abstract.startswith("이 연구는")
    assert a.keywords == ["Digital aging", "Active aging", "Computer"]
    assert a.doi.endswith("ajmahs.2018.8.6.026")


def test_references():
    total, refs = parse_rest_references(samples.REST_REFERENCES)
    assert total == 82557
    assert len(refs) == 2
    assert refs[0]["article_id"] == "ART002703100"
    assert "최유찬" in refs[0]["text"]


def test_citation():
    total, rows = parse_rest_citation(samples.REST_CITATION)
    assert total == 2678
    assert len(rows) == 1
    r = rows[0]
    assert r.get("journal-name") == "영유아교육과정연구"
    assert r.get("impactFactor") == "8.167"
    assert r.get("journal-id") == "SER000002778"


def test_citation_detail():
    total, rows = parse_rest_citation(samples.REST_CITATION_DETAIL)
    assert total == 1
    r = rows[0]
    assert r.get("journal-kor-name") == "현대유럽철학연구"
    assert r.get("kci-registration") == "KCI 등재"
    assert r.get("impactFactor") == "0.61"


def test_rest_error_raises():
    with pytest.raises(ParseError):
        parse_rest_articles(samples.REST_ERROR)
