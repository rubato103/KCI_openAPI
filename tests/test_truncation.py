"""절단(max_records) 가시화 회귀 테스트 — 네트워크 없이 _call 모킹.

배경: 상한에 걸린 결과가 조용히 반환되면 불완전한 코퍼스를 완전한 것으로 오인하게 된다.
실제로 '학부모' 수집에서 3,000 → 6,000 건이 연속으로 상한값과 정확히 일치했고,
축별 total 을 직접 실측하기 전까지 절단 사실이 드러나지 않았다. 그 재발을 막는다.
"""
from kci_mcp.client import KciClient
from tests import samples

# total=3779 인데 record 는 1건 → 항상 절단 상태인 샘플
MANY = samples.REST_ARTICLE_SEARCH
# total=1 / record 1건 → 절단 아님
EXACT = samples.REST_ARTICLE_SEARCH.replace("<total>3779</total>", "<total>1</total>")


def _client(monkeypatch, xml=MANY):
    c = KciClient(api_key="TEST", throttle=0)
    monkeypatch.setattr(c, "_call", lambda api_code, params: xml)
    return c


def test_search_meta_reports_total_and_truncation(monkeypatch):
    c = _client(monkeypatch)
    recs, meta = c.search_meta("컴퓨터", max_records=100)
    assert len(recs) == 1
    assert meta["total"] == 3779
    assert meta["fetched"] == 1
    assert meta["truncated"] is True


def test_search_meta_not_truncated_when_complete(monkeypatch):
    c = _client(monkeypatch, xml=EXACT)
    _, meta = c.search_meta("컴퓨터", max_records=100)
    assert meta["total"] == 1
    assert meta["truncated"] is False


def test_search_wrapper_still_returns_list(monkeypatch):
    """기존 호출부 호환 — search() 는 여전히 list[Article]."""
    c = _client(monkeypatch)
    recs = c.search("컴퓨터", max_records=100)
    assert isinstance(recs, list) and recs[0].arti_id == "ART001143784"


def test_search_terms_meta_records_both_axes(monkeypatch):
    """기본 fields=(title, keyword) → 축 2개가 각각 실행되고 total 이 축별로 남는다."""
    c = _client(monkeypatch)
    recs, meta = c.search_terms_meta(["컴퓨터"], max_records=100)
    assert meta["axes_planned"] == 2 and meta["axes_run"] == 2
    assert [a["field"] for a in meta["axes"]] == ["title", "keyword"]
    assert meta["union"] == 1            # 두 축이 같은 논문 → 합집합 1건
    assert meta["union_upper_bound"] == 3779 * 2
    assert meta["truncated"] is True
    assert "max_records" in meta["warning"]


def test_search_terms_meta_stops_early_and_flags(monkeypatch):
    """상한에 먼저 걸리면 남은 축을 돌지 못한 사실(axes_run < axes_planned)이 드러나야 한다."""
    c = _client(monkeypatch)
    _, meta = c.search_terms_meta(["컴퓨터", "교육"], max_records=1)
    assert meta["axes_run"] < meta["axes_planned"]
    assert meta["truncated"] is True


def test_search_terms_meta_clean_run_not_flagged(monkeypatch):
    c = _client(monkeypatch, xml=EXACT)
    _, meta = c.search_terms_meta(["컴퓨터"], max_records=100)
    assert meta["truncated"] is False
    assert "warning" not in meta


def test_contains_filter_counted_in_meta(monkeypatch):
    c = _client(monkeypatch, xml=EXACT)
    recs, meta = c.search_terms_meta(["컴퓨터"], max_records=100, contains=["존재하지않는단어"])
    assert recs == []
    assert meta["contains_filtered_out"] == 1
    assert meta["returned"] == 0
