#!/usr/bin/env python3
"""
ai-fit-trainer — AI 피트니스 트레이너 MCP 서버.

카카오 PlayMCP 등록용. 외부 API 의존 없이 순수 규칙 기반으로
① 고민/상태 텍스트를 6케이스로 감지해 코칭 조언을 주고,
② 통증 부위에 맞춰 대체 운동을 추천하고,
③ 강도별 회복 루틴을 제공하고,
④ 목표/수준/시간/장비 기반 오늘의 운동 플랜을 생성한다.
모든 도구는 무상태.

Transport: Streamable HTTP (PlayMCP 요구사항), 엔드포인트 /mcp, 0.0.0.0:$PORT(기본 8080).
"""

from __future__ import annotations

import os
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

import rules

# ─────────────────────────── 서버 초기화 ───────────────────────────

PORT = int(os.environ.get("PORT", "8080"))

mcp = FastMCP(
    "ai-fit-trainer",
    instructions=(
        "AI 피트니스 트레이너 도구 모음. 사용자의 고민/상태 텍스트에서 부상·정체기·"
        "식단 거부감·타인 비교·피로·입문 막막함 6가지 케이스를 감지해 코칭하고, "
        "통증 부위별 대체 운동, 강도별 회복 루틴, 목표 기반 오늘의 운동 플랜을 만든다. "
        "모든 도구는 일반적인 운동 안내이며 의료 진단을 대체하지 않는다."
    ),
    host="0.0.0.0",
    port=PORT,
)


# ─────────────────────────── Tool 1: coach_advice ───────────────────────────


@mcp.tool(
    name="coach_advice",
    annotations={
        "title": "AI 트레이너 코칭 조언",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def coach_advice(
    message: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "사용자가 말한 운동/컨디션 관련 고민을 그대로 옮긴 자유 텍스트. "
                "예: '무릎이 시큰거려요', '벤치가 3주째 그대로예요', '닭가슴살 진짜 못 먹겠어요', "
                "'친구는 잘하는데 저만 뒤처지는 것 같아요', '요즘 너무 지쳤어요', "
                "'운동 처음인데 뭐부터 해야 할지 모르겠어요'"
            ),
        ),
    ],
) -> str:
    """AI 피트니스 트레이너 (AI Fit Trainer)의 코칭 상담 도구 — 사용자의 고민/상태 텍스트에서 6가지 케이스를 감지해 맞춤 코칭 조언을 반환한다.

    언제 호출하나: 사용자가 단순 정보 질의가 아니라 감정·컨디션·고민을 토로할 때
    가장 먼저 호출한다. 예를 들어 통증 호소("무릎이 아파요"), 정체기 호소
    ("3주째 안 늘어요"), 식단 거부감("식단이 너무 힘들어요"), 타인과 비교하며
    좌절("남들보다 뒤처지는 것 같아요"), 피로/번아웃("너무 지쳤어요"), 운동을
    막 시작해서 막막함("뭐부터 해야 할지 모르겠어요")이 감지 대상이다.
    구체적인 대체 운동·회복 루틴·운동 플랜이 필요하면 각각 substitute_exercise,
    recovery_routine, plan_workout을 이어서 호출하라.

    감지 케이스와 코칭 원칙:
    - injury(부상·통증): 안전 최우선, 해당 부위 부담 낮추고 48시간 지속 시 병원 상담 안내
    - plateau(정체기): 변수 하나만 바꿔 2주 시도
    - diet_resist(식단 거부감): 강요 없이 대체 옵션 + 80/20 원칙
    - compare(타인 비교 좌절): 비교 중단, 자기 baseline 대비 진전으로 관점 전환
    - fatigue(피로·번아웃): 강도 낮춰도 된다는 허락, 휴식도 훈련이라는 관점
    - onboard_fresh(입문 막막함): 첫 주는 빈도·시간만 단순하게

    매칭되는 케이스가 없으면 일반적인 격려와 함께 상태를 더 구체화해달라는 질문을 반환한다.
    부상(injury) 케이스가 감지되면 "48시간 이상 지속되면 병원 상담" 안전 문구가 항상 포함된다.

    Args:
        message: 사용자 고민/상태 자유 텍스트 (필수)

    Returns:
        str: 감지된 케이스 라벨 + 코칭 원칙 + 구체적 조언(+부상 시 안전 문구) + disclaimer로
        구성된 한국어 텍스트. 케이스 미매칭 시 일반 격려+구체화 질문을 반환한다.
    """
    return rules.build_coach_response(message)


# ─────────────────────────── Tool 2: substitute_exercise ───────────────────────────


@mcp.tool(
    name="substitute_exercise",
    annotations={
        "title": "부위별 대체 운동 추천",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def substitute_exercise(
    pain_area: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "통증·불편을 느끼는 신체 부위. 예: '무릎', '허리', '어깨', '발목', "
                "'무릎이 시큰거려요'처럼 문장으로 넘겨도 부위를 자동 인식한다."
            ),
        ),
    ],
    planned_exercise: Annotated[
        str,
        Field(default="", description="원래 하려고 했던 운동 이름 (선택). 예: '스쿼트', '벤치프레스'"),
    ] = "",
) -> str:
    """AI 피트니스 트레이너 (AI Fit Trainer)의 대체 운동 도구 — 통증·불편 부위를 받아 그 부위 부담을 줄인 대체 운동 3종과 주의사항을 반환한다.

    언제 호출하나: 사용자가 특정 신체 부위의 통증/불편을 언급하며 "그럼 뭘 해야 하나요",
    "대신 뭐 할 수 있어요" 처럼 대체 운동을 직접 물을 때, 또는 coach_advice에서
    injury 케이스가 감지된 후 사용자가 구체적인 대체 운동을 요청할 때 호출한다.
    지원 부위: 무릎, 허리, 어깨, 발목. 그 외 부위는 안전 기본 원칙을 안내한다.

    Args:
        pain_area: 통증 부위 (필수). 문장 전체를 넘겨도 키워드로 부위를 인식한다.
        planned_exercise: 원래 계획했던 운동 (선택) — 무엇을 대체하는지 응답에 반영된다.

    Returns:
        str: 인식된 부위 라벨 + 대체 운동 3종(번호 목록) + 주의사항 + disclaimer로
        구성된 한국어 텍스트. 지원하지 않는 부위는 통증 부위 회피 + 범용 대안 안내로 대체한다.
    """
    return rules.build_substitute_response(pain_area, planned_exercise)


# ─────────────────────────── Tool 3: recovery_routine ───────────────────────────


@mcp.tool(
    name="recovery_routine",
    annotations={
        "title": "강도별 회복 루틴",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def recovery_routine(
    intensity: Annotated[
        str,
        Field(
            default="light",
            description=(
                "회복 강도. 'light'=가벼운 회복(15분), 'moderate'=중강도 액티브 회복(30분), "
                "'full'=풀 회복 세션(60분). 기본값 'light'. '가볍게'·'보통'·'강하게' 같은 "
                "한국어 표현도 자동 인식한다."
            ),
        ),
    ] = "light",
) -> str:
    """AI 피트니스 트레이너 (AI Fit Trainer)의 회복 루틴 도구 — 운동 후 또는 휴식일에 진행할 강도별 회복 루틴 단계를 반환한다.

    언제 호출하나: 사용자가 "오늘 쉬고 싶은데 뭘 하면 좋을까요", "회복 루틴 알려줘",
    "가볍게 몸 풀고 싶어요" 처럼 휴식일/회복 활동을 물을 때, 또는 coach_advice에서
    fatigue 케이스가 감지된 후 구체적인 회복 루틴이 필요할 때 호출한다.

    강도 옵션:
    - light: 걷기+스트레칭+호흡 명상 (15분, 피로가 심하거나 입문자 추천)
    - moderate: 바이크/산책+폼롤러+가동성 운동 (30분, 평소 강도 훈련자 추천)
    - full: 유산소+폼롤러+정적 스트레칭+사우나/냉수 샤워 (60분, 고강도 훈련 후 추천)

    Args:
        intensity: "light" | "moderate" | "full" (또는 한국어 표현). 기본값 "light".
            지원하지 않는 값이면 옵션 안내를 반환한다.

    Returns:
        str: 세션 제목 + 단계별 루틴(번호 목록) + 핵심 포인트 + disclaimer로 구성된
        한국어 텍스트.
    """
    return rules.build_recovery_response(intensity)


# ─────────────────────────── Tool 4: plan_workout ───────────────────────────


@mcp.tool(
    name="plan_workout",
    annotations={
        "title": "오늘의 운동 플랜 생성",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def plan_workout(
    goal: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "운동 목표. '근력'|'strength', '체지방감량'|'다이어트'|'fat_loss', "
                "'근비대'|'hypertrophy', '체력'|'지구력'|'endurance', '일반건강'|'general' "
                "중 하나(한국어/영어 모두 인식)."
            ),
        ),
    ],
    level: Annotated[
        str,
        Field(default="beginner", description="운동 수준. '입문'|'beginner'(기본값), '중급'|'intermediate', '상급'|'advanced'."),
    ] = "beginner",
    minutes: Annotated[
        int,
        Field(default=60, description="가용 운동 시간(분). 기본값 60. 최소 10분으로 보정된다."),
    ] = 60,
    equipment: Annotated[
        str,
        Field(
            default="gym",
            description="사용 가능한 장비. '헬스장'|'gym'(기본값, 전체 기구), '홈트'|'집'|'home'(최소 도구), '맨몸'|'none'(무장비).",
        ),
    ] = "gym",
) -> str:
    """AI 피트니스 트레이너 (AI Fit Trainer)의 운동 플랜 도구 — 목표·수준·가용 시간·장비를 받아 오늘 진행할 운동 플랜(워밍업→본운동→쿨다운)을 생성한다.

    언제 호출하나: 사용자가 "오늘 운동 뭐 하면 좋을까요", "체지방 감량 플랜 짜줘",
    "집에서 45분 운동할 건데 뭐 하지" 처럼 구체적인 오늘의 운동 구성을 물을 때 호출한다.
    coach_advice의 onboard_fresh 케이스 이후 사용자가 목표를 알려주면 이어서 호출하기 좋다.

    구성 로직:
    - 총 시간의 약 15%는 워밍업, 15%는 쿨다운, 나머지 70%는 본운동으로 배분(각 최소 시간 보정)
    - 본운동은 목표(strength/fat_loss/hypertrophy/endurance/general) x 장비(gym/home/none)
      조합별로 미리 정의된 3종 운동 세트를 세트x횟수 또는 시간과 함께 제시
    - 수준(beginner/intermediate/advanced)에 따라 강도 조절 팁을 마지막에 덧붙임

    Args:
        goal: 운동 목표 (필수, 한국어/영어 별칭 인식)
        level: 운동 수준 (기본값 "beginner")
        minutes: 가용 시간(분) (기본값 60)
        equipment: 사용 가능 장비 (기본값 "gym")

    Returns:
        str: 목표/수준/시간/장비 요약 헤더 + 워밍업 + 본운동(번호 목록, 세트x횟수/시간) +
        쿨다운 + 수준별 강도 팁 + disclaimer로 구성된 한국어 텍스트. goal을 인식하지 못하면
        지원 목표 목록을 안내한다.
    """
    return rules.build_workout_plan(goal=goal, level=level, minutes=minutes, equipment=equipment)


# ─────────────────────────── 엔트리포인트 ───────────────────────────

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
