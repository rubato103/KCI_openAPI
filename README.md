# kci-openapi-mcp

한국연구재단(NRF) **KCI(Korea Citation Index) Open API** 문헌·인용지수 검색·수집을 위한
**MCP 서버 + CLI** (개발 중). 자매 프로젝트 [scienceon-mcp](../scienceon)와 동일 아키텍처.

## 무엇을 하나
- 논문 검색·상세(서지·**국문/영문 초록**·키워드·저자)
- 참고문헌 원형 수집
- 저널(학술지) 인용지수·등재이력 조회
- 대량 수집 → xlsx / csv / json / sqlite

## 현재 상태
- ✅ 공식 API 명세 정리 완료 → **[docs/KCI_API_GUIDE.md](docs/KCI_API_GUIDE.md)**
- ⏭️ 구현 예정: `src/kci_mcp/` (client / parser / models / server / cli)

## 빠른 참조
| 항목 | 값 |
|---|---|
| Base URL | `https://open.kci.go.kr/po/openapi/openApiSearch.kci` |
| 응답 | XML (UTF-8) |
| 인증 | `key` 쿼리 파라미터 1개 (open.kci.go.kr 발급, 토큰 불필요) |
| API | articleSearch · articleDetail · referenceSearch · citation · citationDetail |

## 자격증명
환경변수 `KCI_API_KEY` 또는 `.env`에 설정. 인증키는 **커밋·로그 금지**.

## 라이선스
MIT (예정)
