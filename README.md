# kci-openapi-mcp

한국연구재단(NRF) **KCI(Korea Citation Index)** 문헌·인용지수 검색·수집 **MCP 서버 + CLI**.
**REST Open API**(키워드 검색)와 **OAI-PMH**(무인증 대량 수확)를 **혼용**한다.
자매 프로젝트 [scienceon-mcp](../scienceon)와 동일 아키텍처.

## 무엇을 하나
- 논문 검색·상세 (서지 · **국문/영문 초록** · 키워드 · 저자/소속)
- **OAI-PMH 대량 수확** (인증키 불필요 — 세트+날짜범위)
- 참고문헌 원형 수집 · 저널 인용지수/등재이력 (REST 전용)
- 대량 수집 → xlsx / csv / json / sqlite

## 두 인터페이스
| | REST Open API | OAI-PMH |
|---|---|---|
| 엔드포인트 | `…/po/openapi/openApiSearch.kci` | `…/oai/request` |
| 인증 | `KCI_API_KEY` 필요 | **불필요** |
| 질의 | 키워드 검색(title 필수) | 세트+날짜 대량 수확 |
| 인용지수·참고문헌 | ✅ | ❌ |
규격: [docs/KCI_API_GUIDE.md](docs/KCI_API_GUIDE.md) · [docs/KCI_OAI_PMH_GUIDE.md](docs/KCI_OAI_PMH_GUIDE.md) · 설계: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 현재 상태
- ✅ `src/kci_mcp/` 구현 완료 (config/models/parser/oai_client/client/router/exporters/server/cli)
- ✅ **OAI-PMH 라이브 검증 완료**(무인증) · REST 파서 오프라인 검증(공식 예제 XML) · pytest 17건 통과
- ⏭️ REST 라이브 검증은 **인증키 발급 후**

## 설치 / 실행
```bash
uv sync                 # venv는 UV_PROJECT_ENVIRONMENT 로 클라우드 폴더 밖 권장
# CLI (OAI는 키 없이 즉시 사용)
kci identify
kci sets
kci harvest --set ARTI --from 2024-01-01 --until 2024-12-31 --contains 학부모 --max 500 --out output/parent_kci
kci collect --config config/search.example.yaml
# REST (인증키 필요)
kci search --title 학부모 --rows 20
kci detail --id ART002358582
```

### MCP 도구
`kci_status` · `kci_search` · `kci_detail` · `kci_references` · `kci_journal_citation` · `kci_harvest` · `kci_collect`
`kci_collect` 은 요청 성격·키 유무로 REST↔OAI 자동 선택.

## 자격증명 / 네트워크
- `KCI_API_KEY` (open.kci.go.kr 발급) → `.env`(gitignore) 또는 OS 환경변수. **커밋·로그 금지.** OAI는 키 불필요.
- 교육망/사내망 **SSL 인터셉션**은 `truststore`로 OS 신뢰저장소를 사용해 통과(검증 유지). `KCI_OS_TRUST=0`로 비활성.

## 라이선스
MIT
