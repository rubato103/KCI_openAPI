# KCI OAI-PMH 개발 가이드

> 한국연구재단(NRF) **KCI** 메타데이터 **대량 수확(harvesting) 프로토콜** — OAI-PMH 2.0.
> 원본 공식 문서: `reference/KCI OAI-PMH 활용가이드.pdf`(19p, 비공개·gitignore).
> ✅ **라이브 검증됨 (2026-06-22)** — Identify/ListSets/ListMetadataFormats/ListRecords(oai_kci·oai_dc)/
> GetRecord 가 본 명세대로 동작 확인. 검증 메모는 §10.
> ※ KCI는 **두 가지** 공개 인터페이스를 제공한다 — 키워드 검색형 REST([KCI_API_GUIDE.md](KCI_API_GUIDE.md))와
> 본 문서의 **OAI-PMH 대량 수확형**. 용도가 다르므로 상호보완으로 쓴다(§8 비교표).

---

## 0. 한눈에

| 항목 | 값 |
|---|---|
| Base URL | `https://open.kci.go.kr/oai/request` |
| 프로토콜 | **OAI-PMH 2.0** (Open Archives Initiative – Protocol for Metadata Harvesting) |
| 요청 방식 | **GET** (`verb=` + 파라미터) |
| 응답 포맷 | XML (UTF-8), 루트 `<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">` |
| 🔓 **인증** | **없음 — 인증키 불필요!** (REST Open API와 가장 큰 차이) |
| 저장소 | repositoryName = "KCI Open Access Repository", adminEmail = kciadmin@nrf.re.kr |
| 최초생성일 | earliestDatestamp = **2013-03-21**, deletedRecord = no, granularity = **YYYY-MM-DD** |
| 식별자 체계 | `oai:kci.go.kr:ARTI/<내부일련번호>` (예: `oai:kci.go.kr:ARTI/914`) — ⚠️ 이 번호는 artiId(ART…)와 **다름** |
| 페이징 | **resumptionToken** (배치 100건/페이지) |

**6개 verb**
| # | verb | 설명 | 핵심 파라미터 |
|---|---|---|---|
| 1 | `Identify` | 저장소 정보 | — |
| 2 | `ListSets` | 세트 구성 조회 | — |
| 3 | `ListIdentifiers` | 레코드 헤더(식별자) 목록 | metadataPrefix(필수), from, until |
| 4 | `ListMetadataFormats` | 사용 가능한 메타데이터 형식 | — |
| 5 | `ListRecords` | **전체 레코드 대량 수확** | set, metadataPrefix(필수), from, until, resumptionToken |
| 6 | `GetRecord` | 레코드 1건 상세 | identifier(필수), metadataPrefix |

**세트(ListSets) — `set` 파라미터 값**
| setSpec | setName |
|---|---|
| `ARTI` | Article (학술지논문) |
| `ARTI_CONF` | Conference Article (학술대회논문) |
| `JOUR` | Journal (학술지) |

**메타데이터 형식(metadataPrefix)**
| prefix | 설명 | schema |
|---|---|---|
| `oai_dc` | Dublin Core (표준·간략) | http://www.openarchives.org/OAI/2.0/oai_dc.xsd |
| `oai_kci` | **KCI 확장(상세·구조화)** | http://www.kci.go.kr/kciportal/OAI/oai_kci.xsd |

> 🔑 **핵심 활용 포인트**
> - **키 없이** 즉시 사용 가능. REST API의 `title 필수` 제약이 없음 — **세트+날짜범위로 전수 수확**.
> - `oai_kci` 형식은 **국문/영문 초록·저자소속·DOI/UCI·피인용수**까지 구조화 제공 → 초록 백필원.
> - 단, **키워드 검색 불가**(set+date만). 특정 주제(예: 학부모) 수집은 *날짜범위 수확 후 로컬 필터* 필요.

---

## 1. Identify — 저장소 정보

```
GET https://open.kci.go.kr/oai/request?verb=Identify
```
응답 주요 필드: `repositoryName`, `baseURL`, `protocolVersion`(2.0), `adminEmail`,
`earliestDatestamp`(2013-03-21), `deletedRecord`(no), `granularity`(YYYY-MM-DD),
`description/oai-identifier`(scheme=oai_dc, repositoryIdentifier=`oai:kci.go.kr:ARTI/`, sampleIdentifier=`oai:kci.go.kr:ARTI/8820`).

---

## 2. ListSets — 세트 구성

```
GET …/oai/request?verb=ListSets
```
응답: `ListSets/set[]` → `setSpec` + `setName`. (현재 ARTI / ARTI_CONF / JOUR — §0 표)

---

## 3. ListIdentifiers — 식별자(헤더) 목록

```
GET …/oai/request?verb=ListIdentifiers&metadataPrefix=oai_dc&from=2023-01-01&until=2023-01-31
```
| 파라미터 | 필수 | 샘플 | 설명 |
|---|:--:|---|---|
| `verb` | O | ListIdentifiers | |
| `metadataPrefix` | **O** | oai_dc | 반환 XML 메타데이터 접두사 |
| `from` | X | 2023-01-01 | 시작일자 (YYYY-MM-DD) |
| `until` | X | 2023-01-31 | 종료일자 (YYYY-MM-DD) |

응답: `ListIdentifiers/header[]` → `identifier`(예 `oai:kci.go.kr:ARTI/914`) + `datestamp` + `setSpec`.
> 메타데이터 본문 없이 **헤더만** → 어떤 식별자가 있는지 가볍게 훑어 GetRecord 대상 선별에 사용.

---

## 4. ListMetadataFormats — 메타데이터 형식

```
GET …/oai/request?verb=ListMetadataFormats
```
응답: `metadataFormat[]` → `metadataPrefix` + `schema` + `metadataNamespace`. (oai_dc / oai_kci — §0 표)

---

## 5. ListRecords — 전체 레코드 대량 수확 ★

```
GET …/oai/request?verb=ListRecords&set=ARTI&metadataPrefix=oai_kci&from=2023-01-01&until=2023-01-31
```
| 파라미터 | 필수 | 샘플 | 설명 |
|---|:--:|---|---|
| `verb` | O | ListRecords | |
| `set` | X | ARTI | ListSets의 setSpec |
| `metadataPrefix` | **O** | oai_dc / oai_kci | 반환 형식 |
| `from` | X | 2023-01-01 | 시작일자 (YYYY-MM-DD) |
| `until` | X | 2023-01-31 | 종료일자 (YYYY-MM-DD) |
| `resumptionToken` | X | `1900-01-01:9999-12-31:100:200` | 다음 페이지 토큰 |

응답: `ListRecords/record[]` + 끝에 `<resumptionToken>`. 각 record = `header`(identifier/datestamp/setSpec) + `metadata`.

### 5-1. 페이징 (resumptionToken)
- 한 응답에 **100건** 단위. 응답 말미 `<resumptionToken>2023-01-01:2023-01-31:100:1014</resumptionToken>`.
- 토큰 형식(관측): `{from}:{until}:{배치크기}:{총건수 또는 커서}`. **다음 페이지**는 토큰을 그대로
  `&resumptionToken=<값>`으로 재요청. (이때 set/from/until/metadataPrefix는 토큰에 포함되므로 생략)
- 토큰이 비거나 없으면 마지막 페이지 → 종료.

### 5-2. metadataPrefix = `oai_dc` (Dublin Core)
| 요소 | 설명 |
|---|---|
| `dc:title [lang=original\|english]` | 원어/영어 제목 |
| `dc:creator` | `저자1(소속1);저자2(소속2);…` |
| `dc:subject` | 연구분야 |
| `dc:identifier [type=…]` | journalInfo(권호정보)·conferenceInfo·artiId(논문ID)·citedCnt(피인용)·doi·uci·regularity(정규논문여부); 속성 issn·eissn |
| `dc:description [lang=original\|english]` | **원어/영어 초록** |
| `dc:publisher` | 발행기관명 |
| `dc:date` | 발행년월 (YYYY-MM) |
| `dc:type` | Article(학술지논문)·Conference Article·Journal(학술지) |
| `dc:format` | 원문파일 확장자 (예: pdf) |
| `dc:source` | 논문 URL |
| `dc:url` | KCI 논문 URL |
| `dc:language` | 논문 언어 |
| `dc:rights` | 원문 공개 여부 |

### 5-3. metadataPrefix = `oai_kci` (KCI 확장·상세) ★
루트 `<oai_kci xmlns="http://www.kci.go.kr/kciportal/OAI/">`
```
journalInfo
├─ journal-name / pissn / eissn / publisher-name
├─ pub-year (YYYY) / pub-mon (MM)
├─ volume / issue / serno(통권)
articleInfo [article-id="ART…"]
├─ article-categories               연구분야
├─ article-regularity (Y/N)         정규논문여부
├─ title-group → article-title [lang=original|english]
├─ author-group → author            "저자명(소속기관)"
├─ author-name → author → name / affiliation     (저자명·소속 분리)
├─ abstract-group → abstract [lang=original|english]   ★ 국문/영문 초록
├─ language / fpage / lpage / orte-open-yn(원문공개여부)
├─ doi / uci / citation-count
├─ url / verified (Y/N)
```
> `oai_kci`는 REST `articleSearch` 출력과 거의 동급 + **저자·소속 분리(author-name)** 제공.
> **키 없이** 이 수준의 구조화 메타데이터를 대량 수확할 수 있음 = 프로젝트 관점 최대 강점.

---

## 6. GetRecord — 레코드 1건 상세

```
GET …/oai/request?verb=GetRecord&identifier=oai:kci.go.kr:ARTI/914&metadataPrefix=oai_kci
```
| 파라미터 | 필수 | 샘플 | 설명 |
|---|:--:|---|---|
| `verb` | O | GetRecord | |
| `identifier` | **O** | oai:kci.go.kr:ARTI/11138616 | 레코드 식별자 |
| `metadataPrefix` | (PDF상 X) | oai_dc / oai_kci | 반환 형식 — **사실상 필수**(OAI 표준), 예제에도 항상 포함 |

응답: `GetRecord/record` (구조는 ListRecords의 record 1건과 동일, oai_dc/oai_kci 선택).
> ⚠️ `identifier`는 `oai:kci.go.kr:ARTI/<내부번호>` 형식이고 이 내부번호는 **artiId(ART…)와 다르다**.
> 따라서 artiId만 알 때 바로 GetRecord 불가 — 식별자는 ListIdentifiers/ListRecords로 먼저 확보해야 함.

---

## 7. 에러 (OAI-PMH 표준 에러코드)

| 에러코드 | 메시지 | 설명 |
|---|---|---|
| `badArgument` | `#파라미터# parameter is not found` / `… is an illegal parameter` / `… must have 'YYYY-MM-DD'(ex. 2001-01-01) format` | 파라미터 누락·부정·날짜형식 오류 |
| `badResumptionToken` | `Not valid resumptionToken string` | resumptionToken 형식 오류 |
| `noRecordsMatch` | `The combination of the values of arguments results in an empty set` | 검색결과 없음 |

---

## 8. REST Open API vs OAI-PMH — 어떤 걸 언제

| | **Open API Service** (REST) | **OAI-PMH** (본 문서) |
|---|---|---|
| 엔드포인트 | `…/po/openapi/openApiSearch.kci` | `…/oai/request` |
| 인증 | **key 필수**(발급·등록) | **불필요** 🔓 |
| 질의 모델 | 키워드 검색(**title 필수**) | 세트+날짜범위 대량 수확 |
| 특정 주제 검색 | ✅ title/author/journal/keyword/abstract/doi… | ❌ set+date만 (로컬 필터 필요) |
| 전수/대량 수집 | page 루프(displayCount≤100) | ✅ resumptionToken |
| 증분(변경분) 수집 | reg/modDate 필터 | ✅ from/until + datestamp |
| 국문/영문 초록 | ✅ | ✅ (oai_kci) |
| 저자·소속 분리 | articleDetail에서 | ✅ oai_kci `author-name` |
| 논문 피인용수 | ✅ | ✅ |
| 저널 인용지수(IF) | ✅ citation/citationDetail | ❌ |
| 참고문헌 | ✅ referenceSearch | ❌ |

**프로젝트 권장 조합**
- **타깃 주제 수집(학부모 등)** → REST `articleSearch?title=…` (정밀, 단 키 필요)
- **키 발급 전 / 대량·증분 백필 / 초록 보강** → OAI-PMH `ListRecords(oai_kci)` + 날짜범위 + 로컬 필터
- **저널 인용지수·참고문헌** → REST 전용 (OAI-PMH 미제공)

---

## 9. 구현 메모

- **무인증**: OAI-PMH 클라이언트엔 key 주입 불필요. REST 클라이언트와 별도 모듈/엔드포인트로 분리.
- **resumptionToken 루프**: 첫 요청(set+prefix+from+until) → 응답 토큰으로 재요청 반복. 토큰만 전달(다른
  파라미터 동반 금지가 OAI 표준). 빈 토큰/없음이면 종료. 정중한 throttle·백오프 유지.
- **두 형식**: 가벼운 헤더 훑기는 `oai_dc`/ListIdentifiers, 본 수집은 `oai_kci`(상세) 권장.
- **식별자 주의**: `oai:kci.go.kr:ARTI/<번호>` ≠ artiId. 매핑은 record 내부 `artiId`/`article-id`로.
- **XML 파싱**: 네임스페이스 주의 — `oai_dc`는 `dc:`/`oai_dc:` 네임스페이스, `oai_kci`는 KCI 네임스페이스.
  PDF의 `lang=“original”`은 전각 따옴표로 보이나 실제 응답은 표준 `"`(PDF 폰트 문제).
- **원본 XML은 `raw`로 보존**, 정규화 스키마는 REST `models.py`와 공유 가능(Article 공통).

---

## 10. 라이브 검증 메모 (2026-06-22, `src/kci_mcp/oai_client.py`)

무인증으로 실제 엔드포인트 호출해 확인한 사항:
- **Identify/ListSets/ListMetadataFormats** 응답이 §0 표와 정확히 일치(세트 ARTI/ARTI_CONF/JOUR, 형식 oai_dc/oai_kci, earliestDatestamp 2013-03-21).
- **ListRecords(oai_kci)**: arti_id·저자(소속 포함)·국문/영문 초록·DOI·citation-count·resumptionToken 정상 파싱.
  실측 일부 논문은 **국문 초록 없이 영문(original)만** 존재 → 백필 시 lang 분기 필수.
- **GetRecord / oai_dc** 동작 확인. oai_dc 의 `date`(YYYY-MM) → pub_year/pub_mon 분해, identifier[type] 매핑 정상.
- ⚠️ **datestamp = 저장/수정일**(발행일 아님). 그래서 `from/until`은 *발행연도 필터가 아니라 리포지토리 갱신일 필터*다.
  예: `from=until=2024-03-01` 결과에 2003·2014년 **발행** 논문이 포함됨(그날 갱신/적재). 발행연도 필터는 수확 후 `pub_year` 로 로컬 처리.
- ⚠️ **교육망(학교/교육청)·사내망 SSL 인터셉션**: 자체서명 루트 CA가 OS 신뢰저장소에 심겨 있어
  requests(certifi)는 검증 실패 → 클라이언트가 `truststore` 로 **OS 신뢰저장소**를 쓰게 해 통과(검증 유지).
  `KCI_OS_TRUST=0` 비활성 / 대안: `REQUESTS_CA_BUNDLE` 로 루트 CA 직접 지정.
  ✅ 서울 초등학교 교실망에서 `kci identify`/수확 통과 확인.

> REST(키 필요) 부분은 인증키 발급 후 동일 방식으로 검증 → [KCI_API_GUIDE.md](KCI_API_GUIDE.md) 갱신할 것.
