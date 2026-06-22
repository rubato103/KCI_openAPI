"""MCP 프로토콜 레벨 스모크 테스트 — 서버를 stdio로 실제 기동해 handshake/list_tools/call_tool 검증.

python 함수 직접호출이 아니라 **실제 MCP 프로토콜**로 서버를 검증한다(클라이언트=mcp SDK).
사용: python scripts/mcp_smoke.py
"""
import asyncio
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(os.path.dirname(sys.executable), "kci-mcp.exe")

EXPECTED = {"kci_status", "kci_search", "kci_detail", "kci_references",
            "kci_journal_citation", "kci_harvest", "kci_collect"}


def _text(result):
    parts = []
    for c in result.content:
        parts.append(getattr(c, "text", ""))
    return "\n".join(parts)


async def main() -> int:
    params = StdioServerParameters(command=SERVER, args=[], cwd=ROOT, env=dict(os.environ))
    print(f"서버 기동: {SERVER}\n  cwd={ROOT}")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            init = await s.initialize()
            print(f"✅ initialize OK — server: {init.serverInfo.name} v{init.serverInfo.version}")

            tools = (await s.list_tools()).tools
            names = {t.name for t in tools}
            print(f"✅ list_tools: {len(tools)}종 — {sorted(names)}")
            missing = EXPECTED - names
            extra = names - EXPECTED
            assert not missing, f"누락 도구: {missing}"
            print(f"   (누락 없음{', 추가:'+str(extra) if extra else ''})")
            # 스키마 점검: 각 도구가 inputSchema 보유 + 설명
            for t in tools:
                assert t.description, f"{t.name} 설명 없음"
                assert t.inputSchema, f"{t.name} 스키마 없음"
            print("✅ 모든 도구 description+inputSchema 보유")

            print("\n--- 도구 호출(프로토콜 경유) ---")
            r = await s.call_tool("kci_status", {})
            print("kci_status:", _text(r)[:160])

            r = await s.call_tool("kci_harvest", {
                "set_spec": "ARTI", "date_from": "2024-12-02", "date_until": "2024-12-02",
                "max_records": 2})
            print("kci_harvest(2건):", _text(r)[:160])

            # 키 있으면 REST 검색도
            if os.environ.get("KCI_API_KEY") or os.path.exists(os.path.join(ROOT, ".env")):
                r = await s.call_tool("kci_search", {"title": "경계선지능", "rows": 2})
                print("kci_search:", _text(r)[:160])

            # 잘못된 인자 → 에러도 정상 처리(크래시 X)
            r = await s.call_tool("kci_detail", {"arti_id": "INVALID_ID_TEST"})
            print("kci_detail(잘못된 id):", _text(r)[:120])
    print("\n✅ MCP 프로토콜 스모크 테스트 통과")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
