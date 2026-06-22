# kci-openapi-mcp — 프로젝트 지침

> 한국연구재단(NRF) **KCI(Korea Citation Index)** 문헌·인용지수 검색·수집기.
> 공개 **MCP 서버 + CLI**. 자매 프로젝트 **scienceon-mcp**(`../scienceon`)와 동일 아키텍처.
> KCI는 **두 가지 공개 인터페이스**를 제공하며 본 프로젝트는 둘 다 다룬다:
> - **REST Open API**(키워드 검색형, 인증키 필요) → [docs/KCI_API_GUIDE.md](docs/KCI_API_GUIDE.md)
> - **OAI-PMH**(대량 수확형, **인증키 불필요**) → [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md)

## 1. 목표
연구 초반 **자료수집 단계**에서 반복 재사용하는 도구. KCI에서 논문 서지·초록·참고문헌·저널
인용지수를 검색·수집해 후속 텍스트마이닝/계량서지 입력 데이터를 안정적으로 생산한다.
ScienceON(KISTI)과 **상호보완**: 수록 범위 교차검증, 국문 초록 백필, KCI 연구분야 분류·인용지수 확보.

## 2. 확정/계획 결정사항
| 항목 | 결정 |
|------|------|
| 언어/런타임 | Python 3.10+ |
| 패키지 관리 | **uv** (pyproject + uv.lock). venv는 **클라우드 폴더 밖** `C:/Users/user/.venvs/kci-openapi-mcp` (`UV_PROJECT_ENVIRONMENT`) |
| 의존성(계획) | mcp(FastMCP), requests, openpyxl, python-dotenv, pyyaml *(pycryptodome 불필요 — KCI는 토큰/AES 없음)* |
| 인터페이스 | 공용 코어 + **MCP 서버(server.py)** + **CLI(cli.py)** |
| 인터페이스(소스) | **REST**(openApiSearch.kci, 키 필요) + **OAI-PMH**(/oai/request, 무인증) — 둘 다 지원 |
| 수집 대상 | 논문(articleSearch/Detail) 우선 → 참고문헌(referenceSearch) → 저널 인용지수(citation/Detail) → OAI-PMH 대량수확 |
| 출력 | xlsx · csv · json · sqlite |
| 공개 | MIT 예정. `.env`·`reference/`·`output/`는 gitignore |

## 3. 구조 (scienceon-mcp 미러, 계획)
```
src/kci_mcp/
  config.py     # .env 로딩, Base URL/엔드포인트(REST + OAI)
  client.py     # REST GET / 페이징(page,displayCount≤100) / 재시도·throttle / 에러매핑
  oai_client.py # OAI-PMH GET(verb) / resumptionToken 루프 / 무인증
  parser.py     # XML 정규화 — REST(MetaData/outputData/record) + OAI(oai_dc/oai_kci), raw 보존
  models.py     # Article / Reference / JournalCitation 스키마(REST·OAI 공통)
  exporters.py  # xlsx/csv/json/sqlite (scienceon 재사용 가능)
  server.py     # MCP 도구 (아래 §5)
  cli.py        # status/search/detail/references/citation/harvest/collect
docs/
  KCI_API_GUIDE.md       # ★ REST API 명세 (PDF 복구본)
  KCI_OAI_PMH_GUIDE.md   # ★ OAI-PMH 명세 (PDF 복구본)
reference/
  KCI Open API Service 활용가이드.pdf   # 공식 원본 REST (gitignore, 비공개)
  KCI OAI-PMH 활용가이드.pdf            # 공식 원본 OAI-PMH (gitignore, 비공개)
config/         # 검색 설정 템플릿 (search.example.yaml)
```
> ※ 현재 폴더에는 **docs/(가이드 2종) + reference/(PDF 2종)만 마이그레이션 완료**. src/·config/·pyproject·mcpb는 개발 단계에서 생성.

## 4. 자격증명 (.env 또는 사용자 환경변수)
- 변수: `KCI_API_KEY` (KCI 발급 인증키 1개) — **REST API 전용**.
- 발급: open.kci.go.kr Open API 신청. **AES/토큰/공인IP 불필요** — 평문 key 쿼리 파라미터로 호출.
- **OAI-PMH는 무인증** — 키 없이 즉시 사용(`/oai/request`). 키 발급 전에도 OAI 검증·수집 가능.
- ⚠️ 인증키는 코드/로그/커밋 금지 — `.env`(gitignore) 또는 OS 사용자 환경변수로만.

## 5. MCP 도구 (계획) — scienceon 도구셋 대응
| 도구 | API | 설명 |
|------|-----|------|
| `kci_status` | (소량 articleSearch / OAI Identify) | 인증키 유효성·연결 점검 |
| `kci_search` | articleSearch | 논문 검색 — title 필수 + 필터(author/journal/keyword/abstract/doi/연월·등록·수정일자) + 페이징 자동 |
| `kci_detail` | articleDetail | Control Number(id)로 상세·초록·키워드·저자 상세 |
| `kci_references` | referenceSearch | 제목 검색어로 참고문헌 원형 수집 |
| `kci_journal_citation` | citation / citationDetail | 저널 인용지수(연도) / 상세(등재이력·연도별 IF) |
| `kci_harvest` | OAI-PMH ListRecords | **무인증** 세트+날짜범위 대량 수확(oai_kci, resumptionToken 자동) |
| `kci_collect` | **라우터**(REST↔OAI 자동) | 요청 성격·키 유무로 백엔드 자동 선택 → 정규화·중복제거 → xlsx/csv/json/sqlite. 설계: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |

> **혼용 원칙**: REST/OAI를 공통 코어(models/parser/exporters) 위 두 클라이언트로 두고, `kci_collect`가
> 라우팅. 키 없으면 자동 OAI 경로, 인용지수·참고문헌은 REST 전용. 상세 라우팅표 → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 6. 핵심 기술사실 (PDF 기준, ⚠️ 라이브 미검증)
### (A) REST Open API
- **Base**: `https://open.kci.go.kr/po/openapi/openApiSearch.kci` (GET, 응답 XML/UTF-8)
- **5 apiCode**: articleSearch · articleDetail · referenceSearch · citation · citationDetail
- **필수키**: articleSearch/referenceSearch=`title`, articleDetail/citationDetail=`id`, citation=`year`+`years`(2~5)
- **페이징**: `page` + `displayCount`(기본10/최대100). 총건수 `outputData/result/total`
- **articleSearch 출력에 국문·영문 초록 포함** → ScienceON 결측 초록 백필원 후보(검증 필요)
- **인증**: 평문 `key`만. 토큰 발급/갱신 없음 (ScienceON 대비 대폭 단순)
- 에러: "등록되지 않은 key", "검색 조건이 없습니다"(title 0-length) 등 → [docs/KCI_API_GUIDE.md](docs/KCI_API_GUIDE.md) §6

### (B) OAI-PMH (무인증 대량 수확)
- **Base**: `https://open.kci.go.kr/oai/request` (GET, `verb=`, OAI-PMH 2.0, XML/UTF-8)
- **6 verb**: Identify · ListSets · ListIdentifiers · ListMetadataFormats · ListRecords · GetRecord
- **세트**: ARTI(논문) · ARTI_CONF(학술대회) · JOUR(학술지) / **형식**: oai_dc(간략) · **oai_kci(상세·초록 포함)**
- **수집 모델**: `set`+`from/until`(YYYY-MM-DD) → `ListRecords`, **resumptionToken**으로 100건씩 전수 페이징
- **인증 불필요** — 키워드 검색은 불가(날짜범위 수확 후 로컬 필터). 상세 → [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md)

## 7. 개발 원칙
- 자격증명은 `.env`/MCP env 블록으로만. 로그·예외에 노출 금지.
- 정중한 호출: throttle(기본 0.5s), 지수 백오프, 페이지네이션 안전장치(새 record 0이면 종료).
- 원본 XML 필드는 `raw`로 보존. 커밋 메시지 한국어, Claude 서명 금지.
- **라이브 검증 우선(추정 금지)** — 인증키 발급 후 각 API 소량 호출로 응답 스키마 확정 → 가이드 "검증됨" 갱신.

## 8. 상태 (2026-06-22)
- ✅ 공식 PDF 2종 → `reference/`(원본) + `docs/`(복구 명세 2종) 마이그레이션 완료.
- ✅ **`src/kci_mcp/` 구현 완료** — config/models/parser/oai_client/client/router/exporters/server/cli.
  pyproject + 외부 venv(`C:/Users/user/.venvs/kci-openapi-mcp`) + `.env.example` + `config/search.example.yaml`.
- ✅ **OAI-PMH 라이브 검증 완료**(무인증): Identify/ListSets/Formats/ListRecords(oai_kci·oai_dc)/GetRecord +
  `학부모` 로컬필터 + exporters 동작 확인. 검증 메모 → [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md) §10.
- ⏭️ 다음: ① KCI 인증키 발급 → **REST 라이브 검증**(client/search/detail/references/citation) →
  ② `kci_collect` 혼용 교차검증·초록 백필을 학부모 코퍼스에 적용 → ③ tests/CI·README·mcpb 패키징.
- ⚠️ **교육망(학교/교육청)·사내망 SSL 인터셉션** 대응: `truststore` 의존성으로 **OS 신뢰저장소** 사용
  (검증 끄지 않음). `KCI_OS_TRUST=0` 로 비활성 가능. 라이브 검증은 서울 초등학교 교실망에서 통과 확인.
- 🔗 연계 연구: `투고논문/학부모 학술동향` (ScienceON 621편 STM 분석) — KCI는 초록 백필·완전성 교차검증원.
