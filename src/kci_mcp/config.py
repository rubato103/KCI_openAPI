"""환경설정 및 자격증명 로딩.

KCI는 두 인터페이스를 가진다.
  - REST Open API : 인증키(`KCI_API_KEY`) 필요 — 평문 key 쿼리 파라미터(토큰/AES 없음)
  - OAI-PMH       : **무인증** — 키 없이 호출

인증키는 코드/로그에 하드코딩하지 않고 `.env`(gitignore) 또는 OS 환경변수에서만 읽는다.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

# .env 를 한 번 로드 (이미 설정된 환경변수는 덮어쓰지 않음)
load_dotenv(override=False)

# 엔드포인트 (필요 시 .env 로 재정의 가능)
REST_API_URL = os.environ.get(
    "KCI_REST_API_URL", "https://open.kci.go.kr/po/openapi/openApiSearch.kci"
)
OAI_URL = os.environ.get(
    "KCI_OAI_URL", "https://open.kci.go.kr/oai/request"
)


def get_api_key() -> str | None:
    """REST 인증키 — 없으면 None (OAI 경로는 키 없이 동작)."""
    return (os.environ.get("KCI_API_KEY") or "").strip() or None


def require_api_key() -> str:
    key = get_api_key()
    if not key:
        raise RuntimeError(
            "KCI_API_KEY 가 설정되지 않았습니다 — REST Open API 호출에는 인증키가 필요합니다. "
            ".env(.env.example 참고) 또는 OS 환경변수로 설정하세요. "
            "(인증키 없이도 OAI-PMH 수확은 가능합니다: kci_harvest)"
        )
    return key


def redact(key: str | None) -> str:
    """로그용 마스킹 (인증키 노출 방지)."""
    if not key:
        return "(none)"
    return f"{key[:4]}…{key[-2:]}" if len(key) > 6 else "***"


_TRUST_INJECTED = False


def use_os_trust() -> bool:
    """OS 신뢰 저장소(Windows/macOS)로 TLS 검증을 위임.

    교육망(학교/교육청)·사내망의 SSL 인터셉션은 자체서명 루트 CA를 OS 신뢰저장소에 심어둔다.
    requests 는 기본적으로 certifi 만 보므로 그 CA를 모른다 → truststore 로 OS 저장소를 쓰게 하면
    **검증을 끄지 않고도** 통과한다. `KCI_OS_TRUST=0` 이면 비활성. (한 번만 주입)
    """
    global _TRUST_INJECTED
    if _TRUST_INJECTED:
        return True
    if (os.environ.get("KCI_OS_TRUST") or "1").strip() in ("0", "false", "no"):
        return False
    try:
        import truststore

        truststore.inject_into_ssl()
        _TRUST_INJECTED = True
        return True
    except Exception:
        return False
