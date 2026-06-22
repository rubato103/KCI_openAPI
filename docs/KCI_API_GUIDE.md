# KCI Open API 개발 가이드

> 한국연구재단(NRF) **KCI(Korea Citation Index) Open API Service** 호출 규격.
> 원본 공식 문서: `reference/KCI Open API Service 활용가이드.pdf`(19p, 비공개·gitignore).
> 이 문서는 PDF 텍스트(한글 폰트 인코딩 깨짐)를 **전부 복구·정리한 개발용 단일 명세**다.
> ⚠️ 아직 **라이브 미검증**(인증키 미발급). 실제 응답 필드/제약은 키 발급 후 소량 호출로 검증할 것.

---

## 0. 한눈에

| 항목 | 값 |
|---|---|
| Base URL | `https://open.kci.go.kr/po/openapi/openApiSearch.kci` |
| 요청 방식 | **GET** (query string) |
| 응답 포맷 | **XML** (UTF-8), 루트 `<MetaData>` |
| 인증 | `key` 파라미터 = KCI 발급 인증키 (open.kci.go.kr 등록) — **AES/토큰 불필요, 평문 key 1개** |
| 페이징 | `page` + `displayCount`(기본 10, **최대 100**) |
| API 종류 | 5개 (`apiCode`로 구분) |

**5개 API (apiCode)**
| # | apiCode | 기능 | 검색 키 | 단위 |
|---|---|---|---|---|
| 1 | `articleSearch` | 논문 기본 정보 조회 | **title(필수)** + 필터 | 논문 |
| 2 | `articleDetail` | 논문 상세 정보 조회 | **id**(Control Number) | 논문 |
| 3 | `referenceSearch` | 참고문헌 정보 조회 | **title(필수)** | 논문의 참고문헌 |
| 4 | `citation` | 저널 인용지수 제공 | **year+years(필수)** | 저널(학술지) |
| 5 | `citationDetail` | 저널 인용지수 상세 | **id**(저널 제어번호) | 저널(학술지) |

> 🔑 **핵심 제약**: `articleSearch`·`referenceSearch`는 `title`이 **필수**다. title을 0-length로 보내면
> "검색 조건이 없습니다" 에러. → 본질적으로 **제목 키워드 검색** 모델. (keyword/abstract 등은 보조 필터)

---

## 1. articleSearch — 논문 기본 정보 조회

```
GET {Base}?apiCode=articleSearch&key=<인증키>&title=<검색어>&page=1&displayCount=100
```

### 1-1. 요청 파라미터
| 항목(영문) | 필수 | 샘플 | 설명 |
|---|:--:|---|---|
| `key` | **O** | 00000001 | KCI 발급 인증키 |
| `apiCode` | **O** | articleSearch | 검색 대상 |
| `title` | **O** | (UTF-8) | 논문 제목 검색어 |
| `author` | X | 홍길동 | 저자 이름 |
| `journal` | X | 테스트학술지 | 저널(학술지) 이름 |
| `doi` | X | 00.0000/TEST… | DOI |
| `institution` | X | 테스트학회 | 발행기관명 (UTF-8) |
| `affiliation` | X | 테스트대학교 | 저자 소속기관명 (UTF-8) |
| `keyword` | X | | 키워드 (UTF-8) |
| `abstract` | X | | 초록 (UTF-8) |
| `dateFrom` | X | 202301 | 발행연월 시작 (**YYYYMM**, 6자리) |
| `dateTo` | X | 202312 | 발행연월 끝 (YYYYMM) |
| `regDateFrom` | X | 20230101 | 등록일자 시작 (**YYYYMMDD**, 8자리) |
| `regDateTo` | X | 20230101 | 등록일자 끝 (YYYYMMDD) |
| `modDateFrom` | X | 20230101 | 수정일자 시작 (YYYYMMDD) |
| `modDateTo` | X | 20230101 | 수정일자 끝 (YYYYMMDD) |
| `page` | X | 1 | 페이지 |
| `displayCount` | X | 10 | 출력 건수 — 기본 10, **최대 100** |
| `sortNm` | X | title / author / pubiYr | 정렬 기준 (제목/저자명/발행일자) |
| `sortDir` | X | asc / desc | 오름차순/내림차순 |

### 1-2. 응답 구조 (outputData)
```
result/total                                  검색 결과 총 건수
record (1건 = 논문 1편)
├─ journalInfo                                저널(학술지) 정보
│  ├─ journal-name                            저널 이름
│  ├─ publisher-name                          발행기관 이름
│  ├─ foreign-listed [name="…"]               해외 등재 여부(+등재명)
│  ├─ pub-year (YYYY) / pub-mon (MM)          발행 연 / 월
│  └─ volume / issue                          권 / 호
└─ articleInfo [article-id="ART…"]            ★ article-id = Control Number(제어번호)
   ├─ article-categories                      연구분야
   ├─ article-regularity (Y/N)                정규논문 여부
   ├─ title-group
   │  └─ article-title [lang=original|foreign|english]   국문/타언어/영문 제목
   ├─ author-group
   │  └─ author [english="영문명"][orc-id="ORCID"]  →  "이름(소속기관)"
   ├─ abstract-group
   │  └─ abstract [lang=original|english]      ★ 국문/영문 초록
   ├─ fpage / lpage                            시작/끝 페이지
   ├─ orte-open-yn (Y/N)                       원문 공개 여부
   ├─ doi / uci
   ├─ citation-count [kci="…"][wos="…"]        피인용 횟수(KCI/WOS)
   ├─ fwci [create-dt="…"][fwci="…"]           FWCI(분야가중 피인용지수)
   ├─ url                                      KCI 상세 URL
   └─ verified (Y/N)                           검증 여부
```

### 1-3. 예제
요청:
```
https://open.kci.go.kr/po/openapi/openApiSearch.kci?apiCode=articleSearch&key=00000001&title=%EC%BB%B4%ED%93%A8%ED%84%B0
```
응답(발췌):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<MetaData>
  <inputData>
    <key>00000001</key>
    <apiCode>articleSearch</apiCode>
    <title><![CDATA[컴퓨터]]></title>
    <page>1</page>
    <displayCount>10</displayCount>
  </inputData>
  <outputData>
    <result><total>3779</total></result>
    <record>
      <journalInfo>
        <journal-name>컴퓨터교육학회논문지</journal-name>
        <publisher-name>한국컴퓨터교육학회</publisher-name>
        <foreign-listed />
        <pub-year>2004</pub-year>
        <pub-mon>09</pub-mon>
        <volume>8</volume>
        <issue>3</issue>
      </journalInfo>
      <articleInfo article-id="ART001143784">
        <article-categories>컴퓨터교육</article-categories>
        <article-regularity>Y</article-regularity>
        <title-group>
          <article-title lang="original"><![CDATA[초등학교 컴퓨터 교과서에 나온 컴퓨터 용어 분석]]></article-title>
          <article-title lang="foreign"><![CDATA[An Analysis of Computer Terms …]]></article-title>
          <article-title lang="english"><![CDATA[An Analysis of Computer Terms …]]></article-title>
        </title-group>
        <author-group>
          <author english="KIM KAP SU" orc-id="0000-0000-0000-0000">김갑수(서울교육대학교)</author>
          <author english="Myunghui Hong">홍명희(서울교육대학교)</author>
          <author>이순영(인천계산초등학교)</author>
        </author-group>
        <abstract-group>
          <abstract lang="original"><![CDATA[ … 국문 초록 … ]]></abstract>
          <abstract lang="english"><![CDATA[ … English abstract … ]]></abstract>
        </abstract-group>
        <fpage>433</fpage>
        <lpage>448</lpage>
        <orte-open-yn>Y</orte-open-yn>
        <doi /><uci />
        <citation-count kci="4" wos="0">4</citation-count>
        <fwci create-dt="2023-07-26" fwci="0.0">0.0</fwci>
        <url><![CDATA[https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001143784]]></url>
        <verified>N</verified>
      </articleInfo>
    </record>
    …
  </outputData>
</MetaData>
```

---

## 2. articleDetail — 논문 상세 정보 조회

```
GET {Base}?apiCode=articleDetail&key=<인증키>&id=<Control Number>
```

### 2-1. 요청 파라미터
| 항목 | 필수 | 샘플 | 설명 |
|---|:--:|---|---|
| `key` | **O** | 00000001 | 인증키 |
| `apiCode` | **O** | articleDetail | |
| `id` | **O** | ART002358582 | Control Number(KCI 논문 제어번호) |

### 2-2. 응답 구조 (articleSearch보다 상세)
```
record
├─ journalInfo [journal-id="SER…"]            ★ journal-id = 학술지 ID
│  ├─ issn
│  ├─ journal-name / publisher-name
│  ├─ kci-registration                        KCI 등재 정보
│  ├─ foreign-registration                    해외 등재 정보
│  └─ pub-year / pub-mon / volume / issue
└─ articleInfo [article-id="ART…"]
   ├─ article-categories                       연구분야 (예: "공학 > 컴퓨터학")
   ├─ article-regularity (Y/N)
   ├─ article-language                         논문 언어 (예: 한국어)
   ├─ title-group → article-title[lang=original|foreign|english]
   ├─ author-group
   │  └─ author [author-id][orc-id][author-part][author-division]
   │     ├─ author-division="1"               주저자
   │     ├─ author-division="2"               교신저자
   │     ├─ <name> (국문 이름)
   │     ├─ <name-eng> (영문 이름)
   │     └─ <institution> (소속)
   ├─ abstract [lang=original|english]
   ├─ keyword-group → keyword (키워드 1건씩)
   ├─ fpage / lpage
   ├─ doi / uci
   ├─ citation-count [kci][wos]
   ├─ url
   └─ verified (Y/N)
```

### 2-3. 예제
```
https://open.kci.go.kr/po/openapi/openApiSearch.kci?apiCode=articleDetail&key=00000001&id=ART002358582
```

---

## 3. referenceSearch — 참고문헌 정보 조회

```
GET {Base}?apiCode=referenceSearch&key=<인증키>&title=<검색어>
```
지정한 검색 조건에 맞는 논문들의 **참고문헌 원형(인용 서지 텍스트)** 목록을 반환.

### 3-1. 요청 파라미터
| 항목 | 필수 | 샘플 | 설명 |
|---|:--:|---|---|
| `key` | **O** | 00000001 | 인증키 |
| `apiCode` | **O** | referenceSearch | |
| `title` | **O** | 컴퓨터교육 | 제목 검색어 (UTF-8) |
| `author` | X | 홍길동 | 저자명 (UTF-8) |
| `institution` | X | 테스트학회 | 발행기관 (UTF-8) |
| `pubiYr` | X | 2023 | 발행 연도 (YYYY) |
| `displayCount` | X | 10 | 기본 10, 최대 100 |
| `sortNm` | X | title/author/pubiYr | 정렬 기준 |
| `sortDir` | X | asc/desc | |

### 3-2. 응답 구조
```
result/total                          검색 결과 총 건수
record [article-id="ART…"]            참고문헌 원형(CDATA 텍스트), article-id=참고문헌 논문ID
```
예: `<record article-id="ART002703100">최유찬, 「문학과 컴퓨터 게임」, 인문과학 85집, 연세대 인문과학연구소, 2003. 12, 1쪽.</record>`

---

## 4. citation — 저널 인용지수 제공

```
GET {Base}?apiCode=citation&key=<인증키>&year=<기준년도>&years=<포함년도>
```
저널(학술지) 단위 인용지수(기본 정보).

### 4-1. 요청 파라미터
| 항목 | 필수 | 샘플 | 설명 |
|---|:--:|---|---|
| `key` | **O** | 00000001 | 인증키 |
| `apiCode` | **O** | citation | |
| `year` | **O** | 2022 | 기준년도 (YYYY) |
| `years` | **O** | 2 | 포함 년도 (**기본 2, 최대 5**) |
| `journal` | X | 테스트학술지 | 저널 이름 (UTF-8) |
| `doi` | X | | DOI |
| `institution` | X | 테스트학회 | 발행기관명 (UTF-8) |
| `modDateFrom` | X | 20230214 | 수정일 시작 (YYYYMMDD) |
| `modDateTo` | X | 20230214 | 수정일 끝 (YYYYMMDD) |
| `page` | X | 1 | |
| `displayCount` | X | 10 | 기본 10, 최대 100 |
| `sortNm` / `sortDir` | X | | title/author/pubiYr · asc/desc |

### 4-2. 응답 구조
```
result/total / year / years
record
├─ journalInfo [journal-id="SER…"]
│  ├─ journal-name / publisher-name
│  ├─ major                            연구분야
│  └─ url
└─ citationInfo
   ├─ impactFactor                     영향력 지수(IF)
   ├─ wosImpactFactor                  WoS 영향력 지수
   ├─ exImpactFactor                   자기인용 제외 IF
   ├─ immediacyIndex                   즉시성 지수
   └─ selfCitedRate                    자기인용 비율
```

---

## 5. citationDetail — 저널 인용지수 상세

```
GET {Base}?apiCode=citationDetail&key=<인증키>&id=<저널 제어번호>
```

### 5-1. 요청 파라미터
| 항목 | 필수 | 샘플 | 설명 |
|---|:--:|---|---|
| `key` | **O** | 00000001 | 인증키 |
| `apiCode` | **O** | citationDetail | |
| `id` | **O** | 001223 | 저널(학술지) 제어 번호 |

### 5-2. 응답 구조
```
record
├─ journalInfo [journal-id]
│  ├─ registration
│  │  ├─ kci-registration              KCI 등재 정보 (등재 후보 / 등재 / 우수 등재)
│  │  └─ foreign-registration          해외 학술지 등재 정보
│  ├─ journal-kor-name / journal-kor-abbr-name      국문명 / 국문 약어
│  ├─ journal-fola-name / journal-fola-abbr-name    타언어명 / 타언어 약어
│  ├─ major                            연구분야 (예: "인문학 > 철학 > 서양철학")
│  ├─ issn / eissn
│  ├─ fsed-yr                          창간년월
│  ├─ impr                             간기(발행 주기)
│  ├─ current-issue                    최근 발행호
│  ├─ use-lang                         사용 언어
│  └─ publisher
│     ├─ publisher-kor-name / publisher-eng-name
│     ├─ publisher-tel / publisher-homp / publisher-addr
├─ journal-change-history
│  └─ journal-change [date][div-cd][registration]   저널 변경 이력 1건
│       div-cd: 1=학술지등록 2=학술지명변경 3=학술지삭제 4=통합 5=분리
│               6=학회명변경 7=등재 8=평가 9=발행기관변경
│       registration: 02=등재 03=등재후보 09=우수등재
└─ journal-citation-index-history
   └─ journal-citation-index [year]               연도별 인용지수 1건
        impactFactor, impactFactor3/4/5            영향력지수(2·3·4·5년)
        wosImpactFactor                            WoS IF
        sjr                                        중심성 지수
        immediacyIndex                             즉시성 지수
        selfCitedRate                              자기인용비율(2년)
        yearsArticles2 / yearsCited2               논문 수(2년) / 피인용 횟수(2년)
        exImpactFactor                             자기인용 제외 IF(2년)
```

---

## 6. 에러 메시지 (§2)

| 에러 메시지 | 설명 |
|---|---|
| 필수 요청 파라미터가 없음 => 파라미터 | 해당 API 필수 파라미터 누락 |
| 등록되지 않은 key 입니다. | 인증키 값이 유효하지 않음 |
| 사용기간이 종료되었습니다. | 인증키 사용기간 만료 |
| 파라미터 범위 오류 => year[시작년도 ~ 종료년도] | year 시작 > 종료 |
| 파라미터 범위 오류 => years[ 2 ~ 5 ] | years는 2 이상 5 이하만 |
| 등록되지 않은 서비스 | apiCode가 유효하지 않음 |
| 검색 조건이 없습니다. | 필수 파라미터는 있으나 검색 조건 미성립 (예: title을 0-length로 전송) |
| #파라미터#의 범위가 맞지 않습니다. | 시작값 > 종료값 |
| #파라미터#은 #제한된 자릿수# 자리 숫자만 가능합니다. | 입력값이 지정 자릿수 초과/불일치 |

---

## 7. 구현 메모 (ScienceON MCP 대비)

- **인증이 압도적으로 단순**: ScienceON은 AES-256-CBC 토큰 발급/갱신이 필요했으나, KCI는 **평문 `key` 쿼리 1개**.
  → `auth.py` 사실상 불필요(키 보관·주입만). 토큰 캐시/갱신 로직 없음.
- **전건 수집**: `displayCount=100` + `page` 증가 루프. `result/total` 기준 종료, 새 record 0이면 안전 종료.
- **title 필수 제약**: 키워드/초록 단독 검색 불가(검증 필요). 키워드 코퍼스가 필요하면 `keyword`/`abstract`
  보조 파라미터 + title 조합 전략을 키 발급 후 실측할 것. (open question)
- **정중한 호출**: throttle(기본 0.5s) + 지수 백오프. 대량 호출 전 소량 시범.
- **XML 파싱**: 루트 `<MetaData>`, 총건수 `outputData/result/total`, 레코드 `outputData/record`.
  속성값 일부가 PDF에서 전각 따옴표(`〞`)로 보이나 실제 응답은 표준 `"`임(PDF 폰트 문제).
- **원본 XML 필드는 `raw`로 보존**, 정규화 스키마는 ScienceON `models.py` 패턴 따름.

> ⚠️ 본 문서 수치/필드는 공식 PDF 기준 **정리본**이며 라이브 미검증. 인증키 발급 후
> 각 API 1~2회 소량 호출로 응답 스키마를 확정하고 본 문서를 "검증됨"으로 갱신할 것.
