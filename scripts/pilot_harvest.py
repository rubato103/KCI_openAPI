"""경계선지능·느린학습자 OAI 시범 수확 (진행상황 로깅).

사용: python scripts/pilot_harvest.py --from 2025-01-01 --until 2025-06-22 [--max-pages N]
⚠️ datestamp=수정일 기준 → 해당 기간 갱신분만(시범 표본). 완전 코퍼스는 REST(키) 또는 전기간 수확.
"""
import argparse
import io
import sys
import time
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "src")

from kci_mcp.exporters import export          # noqa: E402
from kci_mcp.oai_client import KciOaiClient, _contains_any  # noqa: E402
from kci_mcp.parser import parse_oai_records   # noqa: E402

BORDER = ["경계선지능", "경계선 지능", "경계선지적", "경계선 지적",
          "borderline intellectual", "borderline intelligence"]
SLOW = ["느린학습", "느린 학습", "slow learner"]
KW = BORDER + SLOW

ap = argparse.ArgumentParser()
ap.add_argument("--from", dest="dfrom", required=True)
ap.add_argument("--until", required=True)
ap.add_argument("--max-pages", type=int, default=3000)
ap.add_argument("--out", default="output/borderline_slow_pilot")
ap.add_argument("--name", default="borderline_slow_pilot")
a = ap.parse_args()

c = KciOaiClient(timeout=40, throttle=0.2)
params = {"verb": "ListRecords", "metadataPrefix": "oai_kci", "set": "ARTI",
         "from": a.dfrom, "until": a.until}
hits, seen, scanned, pages = [], set(), 0, 0
t0 = time.time()
print(f"수확: ARTI / {a.dfrom}~{a.until} / oai_kci / 변형어 {len(KW)}종", flush=True)
while pages < a.max_pages:
    arts, token = parse_oai_records(c._call(params))
    pages += 1
    scanned += len(arts)
    for x in arts:
        if _contains_any(x, KW):
            k = x.dedup_key()
            if k not in seen:
                seen.add(k)
                hits.append(x)
    if pages % 10 == 0:
        print(f"  page {pages} | scanned {scanned} | hits {len(hits)} | {time.time()-t0:.0f}s", flush=True)
    if not token:
        break
    params = {"verb": "ListRecords", "resumptionToken": token}
    time.sleep(c.throttle)

print(f"완료: pages {pages}, scanned {scanned}, hits {len(hits)}, {time.time()-t0:.0f}s", flush=True)

g, yr = Counter(), Counter()
for x in hits:
    h = "\n".join([x.title, x.title_en, x.abstract, x.abstract_en, x.categories,
                   "; ".join(x.authors), "; ".join(x.keywords)]
                  + [v for v in x.raw.values() if isinstance(v, str)]).lower()
    if any(s.lower() in h for s in BORDER):
        g["경계선지능"] += 1
    if any(s.lower() in h for s in SLOW):
        g["느린학습자"] += 1
    yr[x.pub_year or "?"] += 1
print("그룹:", dict(g))
print("발행연도:", dict(sorted(yr.items())))
print("국문초록:", sum(1 for x in hits if x.abstract), "/ 영문초록:", sum(1 for x in hits if x.abstract_en))
print("--- 샘플 ---")
for x in hits[:12]:
    print(f"  [{x.pub_year}] {x.title[:46]} | {x.journal[:16]} ({x.arti_id})")

if hits:
    for p in export(hits, ["xlsx", "csv", "json"], a.out, a.name):
        print("저장:", p)
