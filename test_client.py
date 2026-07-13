#!/usr/bin/env python3
"""
ai-fit-trainer MCP 서버 테스트 클라이언트.

공식 MCP Python SDK의 streamablehttp_client로 실제 접속해
tools/list 확인 + 5개 검증 케이스를 순서대로 호출한다.

사용법:
    .venv/bin/python server.py &          # 서버 먼저 기동 (기본 8080)
    .venv/bin/python test_client.py       # 접속 테스트
"""

import asyncio
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

PORT = os.environ.get("PORT", "8080")
SERVER_URL = f"http://127.0.0.1:{PORT}/mcp"


def _print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


async def main() -> None:
    _print_header(f"접속 대상: {SERVER_URL}")

    async with streamablehttp_client(SERVER_URL) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ initialize 핸드셰이크 성공")

            # ── tools/list ──
            _print_header("tools/list")
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print(f"등록된 도구 수: {len(tool_names)}")
            for t in tools_result.tools:
                print(f"  - {t.name}: {t.description.strip().splitlines()[0]}")

            expected = {"coach_advice", "substitute_exercise", "recovery_routine", "plan_workout"}
            missing = expected - set(tool_names)
            if missing:
                print(f"❌ 누락된 도구: {missing}")
                sys.exit(1)
            print("✅ 4개 도구 모두 확인됨")

            # ── 검증 1: coach_advice("무릎이 시큰거려요") -> injury 케이스 예상 ──
            _print_header("검증 1: coach_advice('무릎이 시큰거려요') -> 부상 케이스 예상")
            r1 = await session.call_tool("coach_advice", {"message": "무릎이 시큰거려요"})
            text1 = r1.content[0].text
            print(text1)
            assert "부상" in text1 and "48시간" in text1, "❌ 부상 케이스가 아니거나 안전문구 누락"
            print("✅ 부상 케이스 확인")

            # ── 검증 2: coach_advice("벤치가 3주째 그대로예요") -> plateau 케이스 예상 ──
            _print_header("검증 2: coach_advice('벤치가 3주째 그대로예요') -> 정체기 케이스 예상")
            r2 = await session.call_tool("coach_advice", {"message": "벤치가 3주째 그대로예요"})
            text2 = r2.content[0].text
            print(text2)
            assert "정체기" in text2, "❌ 정체기 케이스가 아님"
            print("✅ 정체기 케이스 확인")

            # ── 검증 3: substitute_exercise("무릎") ──
            _print_header("검증 3: substitute_exercise('무릎')")
            r3 = await session.call_tool("substitute_exercise", {"pain_area": "무릎"})
            text3 = r3.content[0].text
            print(text3)
            assert "무릎" in text3 and "Sled" in text3, "❌ 무릎 대체 운동 출력 이상"
            print("✅ 무릎 대체 운동 확인")

            # ── 검증 4: recovery_routine("moderate") ──
            _print_header("검증 4: recovery_routine('moderate')")
            r4 = await session.call_tool("recovery_routine", {"intensity": "moderate"})
            text4 = r4.content[0].text
            print(text4)
            assert "중강도" in text4, "❌ moderate 루틴 출력 이상"
            print("✅ 중강도 회복 루틴 확인")

            # ── 검증 5: plan_workout("체지방 감량", "beginner", 45, "home") ──
            _print_header("검증 5: plan_workout('체지방 감량', 'beginner', 45, 'home')")
            r5 = await session.call_tool(
                "plan_workout",
                {"goal": "체지방 감량", "level": "beginner", "minutes": 45, "equipment": "home"},
            )
            text5 = r5.content[0].text
            print(text5)
            assert "체지방 감량" in text5 and "45분" in text5, "❌ 운동 플랜 출력 이상"
            print("✅ 운동 플랜 확인")

            _print_header("모든 검증 통과 ✅")


if __name__ == "__main__":
    asyncio.run(main())
