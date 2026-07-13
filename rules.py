"""
AI 피트니스 트레이너 — 코칭·대체운동·회복·플랜 규칙 엔진.

원본 TypeScript 규칙(response-patterns.ts / substitute-exercise.ts /
active-recovery.ts / daily-plan.ts)의 케이스 분류·한국어 문구를 Python으로
이식했다. 특정 코치 인물·채널·텔레그램 명령어 언급은 모두 제거하고
범용 "AI 트레이너" 페르소나 + 자연문으로 재작성했다.

모든 함수는 무상태 순수 함수 — 외부 API·DB 의존 없음.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

DISCLAIMER = (
    "⚠️ 본 정보는 일반적인 운동 안내이며, 통증·질환이 있다면 의료 전문가와 상담하세요."
)


def append_disclaimer(body: str) -> str:
    return f"{body}\n\n{DISCLAIMER}"


# ═══════════════════════════════════════════════════════════════════
# 1) 코칭 케이스 6종 — response-patterns.ts 이식
# ═══════════════════════════════════════════════════════════════════

KO_INJURY = re.compile(r"(아파|아프|통증|부상|시큰|쑤시|결리|무릎|허리|어깨|발목|팔꿈치|손목|쥐가)")
KO_PLATEAU = re.compile(r"(정체|안\s*늘|늘지\s*않|똑같|제자리|그대로|진전\s*없|똑같이|변화\s*없|벽|한계)")
KO_DIET_RESIST = re.compile(r"(닭가슴|식단|맛없|먹기\s*싫|질리|싫어|못\s*먹|배고프|치팅|치킨)")
KO_COMPARE = re.compile(r"(나만|남들|다른\s*사람|쟤는|친구는|동료는|뒤처|뒤지|느려|못해)")
KO_FATIGUE = re.compile(r"(피곤|지쳤|힘들|번아웃|쉬고\s*싶|포기|그만|의욕\s*없|동기\s*없)")
KO_ONBOARD_FRESH = re.compile(r"(처음|어떻게\s*시작|뭘\s*해야|어디서부터|초보|모르겠)")


@dataclass
class CoachCase:
    id: str
    label: str
    description: str
    detect: Callable[[str], bool]
    principle: str
    advice: str


COACH_CASES: list[CoachCase] = [
    CoachCase(
        id="injury",
        label="부상·통증 호소",
        description="안전 우선 — 강도를 낮추고 병원 상담 임계 기준 안내",
        detect=lambda t: bool(KO_INJURY.search(t)),
        principle="통증 신호는 무시하면 안 됩니다. 오늘은 해당 부위 부담이 적은 운동으로 대체하는 게 우선이에요.",
        advice=(
            "1) 통증 부위를 쓰는 운동은 오늘 건너뛰고 다른 부위(상체/하체/코어) 운동으로 전환하세요.\n"
            "2) 초기 24시간은 RICE(휴식·냉찜질·압박·거상)를 적용하세요.\n"
            "3) 48시간이 지나도 통증이 지속되면 병원 진료를 받아보는 것을 권장합니다.\n"
            "특정 부위 대체 운동이 필요하면 아픈 부위를 말씀해주세요 — 부담을 줄인 대체 운동을 바로 안내해드려요."
        ),
    ),
    CoachCase(
        id="plateau",
        label="정체기 호소",
        description="데이터 진단 유도 + 변수 한 가지만 바꾸는 전략",
        detect=lambda t: bool(KO_PLATEAU.search(t)),
        principle="정체는 몸이 지금 자극에 적응했다는 신호예요 — 변수를 한 가지만 바꾸면 대부분 풀립니다.",
        advice=(
            "다음 중 딱 하나만 골라 2주간 시도해보세요:\n"
            "1) 휴식일 늘리기 (예: 주 3회 → 주 4회)\n"
            "2) 반복 범위(rep range) 바꾸기 (예: 5×5 → 8×3)\n"
            "3) 보조 운동 추가 (같은 근육군을 다른 각도로 자극)\n"
            "한 번에 여러 변수를 바꾸면 무엇이 효과 있었는지 알 수 없으니 하나씩 시도하는 게 핵심이에요."
        ),
    ),
    CoachCase(
        id="diet_resist",
        label="식단 거부감",
        description="강요하지 않고 대체 옵션 + 80/20 원칙 제시",
        detect=lambda t: bool(KO_DIET_RESIST.search(t)),
        principle="억지로 먹는 식단은 오래 못 갑니다. 지속 가능한 게 결국 이깁니다.",
        advice=(
            "단백질은 g당 같은 양이면 서로 대체 가능해요 — 연어, 소고기 우둔살, 계란흰자, 두부, "
            "그릭요거트 모두 좋은 대안입니다.\n"
            "80/20 원칙: 전체 식단의 80%만 깔끔하게 지키면 나머지 20%는 좋아하는 음식으로 채워도 괜찮아요.\n"
            "완벽한 식단보다 오래 유지할 수 있는 식단이 결과를 만듭니다."
        ),
    ),
    CoachCase(
        id="compare",
        label="타인 비교로 인한 좌절",
        description="비교를 끊고 자신의 baseline 대비 진전으로 reframe",
        detect=lambda t: bool(KO_COMPARE.search(t)),
        principle="타인과의 비교는 동기를 가장 빠르게 죽이는 방법이에요. 출발점·체격·회복력이 모두 다릅니다.",
        advice=(
            "봐야 할 기준은 딱 하나예요 — 한 달 전의 나 vs 지금의 나.\n"
            "처음 시작했을 때 기록을 떠올려보세요. 그때와 지금의 차이가 바로 당신의 진짜 진전입니다.\n"
            "다른 사람의 페이스가 아니라 자신의 페이스로 꾸준히 가는 게 가장 빠른 길이에요."
        ),
    ),
    CoachCase(
        id="fatigue",
        label="피로·번아웃",
        description="강도를 낮춰도 된다는 허락 + 휴식도 훈련이라는 reframe",
        detect=lambda t: bool(KO_FATIGUE.search(t)),
        principle="쉬는 것도 훈련의 일부입니다 — 회복이 없으면 몸이 적응할 시간도 없어요.",
        advice=(
            "오늘은 죄책감 없이 강도를 낮춰도 괜찮습니다. 가벼운 회복 루틴(약 15분) 또는 완전 휴식 중에 고르세요.\n"
            "충분히 쉬고 나면 다음 세션에서 다시 강도를 낼 수 있어요. 오늘의 회복이 다음 성과를 만듭니다.\n"
            "피로가 1~2주 이상 지속되면 수면·영양 상태도 함께 점검해보세요."
        ),
    ),
    CoachCase(
        id="onboard_fresh",
        label="입문 직후 막막함",
        description="첫 주는 단순화 — 빈도·시간만 정하고 시작하는 것 자체에 집중",
        detect=lambda t: bool(KO_ONBOARD_FRESH.search(t)),
        principle="복잡하게 생각하지 마세요. 첫 주는 '시작하는 습관'을 만드는 게 전부입니다.",
        advice=(
            "첫 주 목표는 단 하나 — 주 3회, 회당 30분, 어떤 운동이든 괜찮습니다.\n"
            "몸이 운동 자체에 적응하는 게 우선이에요. 강도나 완성도는 둘째 주부터 신경 써도 늦지 않습니다.\n"
            "목표(체지방 감량/근력/체력)와 사용 가능한 장비를 알려주시면 오늘의 운동 플랜을 바로 짜드릴게요."
        ),
    ),
]


def detect_coach_case(text: str) -> Optional[CoachCase]:
    """우선순위: injury > plateau > diet_resist > compare > fatigue > onboard_fresh (리스트 순서)."""
    for case in COACH_CASES:
        if case.detect(text):
            return case
    return None


def build_coach_response(text: str) -> str:
    case = detect_coach_case(text)
    if case is None:
        body = (
            "💬 지금 상태를 조금 더 알려주시면 더 정확히 도와드릴 수 있어요.\n\n"
            "예를 들어 — 통증이 있는지, 운동이 정체된 느낌인지, 식단이 힘든지, 피로가 쌓였는지, "
            "아니면 아예 처음이라 막막한 건지 알려주세요.\n"
            "일반적으로는 이렇게 진행하는 걸 권장해요: 주 3~4회 운동, 충분한 단백질 섭취, "
            "주 1회 이상 회복일 확보가 기본기입니다."
        )
        return append_disclaimer(body)

    body = f"💬 {case.label}\n\n{case.principle}\n\n{case.advice}"
    if case.id == "injury":
        body += (
            "\n\n🚑 안전 안내: 통증이 48시간 이상 지속되거나 붓기·열감이 동반되면 "
            "반드시 병원 진료를 받으세요."
        )
    return append_disclaimer(body)


# ═══════════════════════════════════════════════════════════════════
# 2) 부위별 대체 운동 — substitute-exercise.ts 이식
# ═══════════════════════════════════════════════════════════════════


@dataclass
class BodyPartInfo:
    label: str
    keywords: list[str]
    alternatives: list[str]
    caution: str


BODY_PARTS: dict[str, BodyPartInfo] = {
    "knee": BodyPartInfo(
        label="무릎",
        keywords=["무릎", "슬개골", "연골"],
        alternatives=[
            "Heavy Sled Pull (당기기 위주, 무릎 굴곡 최소화)",
            "Step-up (낮은 박스, 가벼운 무게)",
            "Bike Erg (좌식, 무릎 충격 없음)",
        ],
        caution="통증이 운동 외 상황에서도 지속되면 알려주세요. 강도는 평소의 80% 이하로 운영하세요.",
    ),
    "back": BodyPartInfo(
        label="허리",
        keywords=["허리", "척추", "디스크"],
        alternatives=[
            "Plank 변형 (Side Plank, Bird Dog)",
            "Glute Bridge (둔근 활성화, 허리 부담 감소)",
            "서스펜션 트레이너 로우 (TRX, 척추 중립 유지)",
        ],
        caution="척추 중립 유지가 핵심입니다. 데드리프트·스쿼트는 오늘은 건너뛰세요.",
    ),
    "shoulder": BodyPartInfo(
        label="어깨",
        keywords=["어깨", "회전근"],
        alternatives=[
            "밴드 풀어파트 (Banded Pull-Apart, 회전근개 자극)",
            "월 슬라이드 (Wall Slide, 가동성+안정성)",
            "랜드마인 프레스 (Landmine Press, 짧은 가동범위)",
        ],
        caution="머리 위로 드는 동작(오버헤드 프레스, 스내치)은 모두 건너뛰세요. 통증 없는 가동범위 안에서만 움직이세요.",
    ),
    "ankle": BodyPartInfo(
        label="발목",
        keywords=["발목", "아킬레스"],
        alternatives=[
            "상체 바이크 (Upper-body Bike)",
            "벤치프레스 / 로우 (좌식 상체 운동)",
            "플랭크 시리즈",
        ],
        caution="점프·달리기는 오늘 모두 쉬세요. 부기가 있다면 RICE(휴식·냉찜질·압박·거상)를 적용하세요.",
    ),
}


def find_body_part(text: str) -> Optional[str]:
    t = text.lower()
    for key, info in BODY_PARTS.items():
        if any(kw.lower() in t for kw in info.keywords):
            return key
    return None


def build_substitute_response(pain_area: str, planned_exercise: str = "") -> str:
    key = find_body_part(pain_area)
    plan_line = f'"{planned_exercise.strip()}" 대신 ' if planned_exercise.strip() else ""

    if key is None:
        body = (
            f"🤖 '{pain_area.strip()}' 부위에 대한 세부 데이터가 아직 없어요.\n\n"
            f"{plan_line}일반 원칙을 안내해드릴게요:\n"
            "1) 통증이 있는 부위를 직접 사용하는 동작은 오늘 피하세요.\n"
            "2) 통증 없는 다른 부위(상체/하체/코어 중 미사용 부위) 운동으로 대체하세요.\n"
            "3) 가벼운 유산소(좌식 바이크, 걷기)로 대체하는 것도 좋은 선택입니다.\n"
            "통증이 심하거나 48시간 이상 지속되면 병원 상담을 권장합니다."
        )
        return append_disclaimer(body)

    info = BODY_PARTS[key]
    listed = "\n".join(f"{i + 1}️⃣ {alt}" for i, alt in enumerate(info.alternatives))
    body = (
        f"🤖 {info.label} 부담을 줄인 대체 운동 {len(info.alternatives)}개를 추천드려요:\n\n"
        f"{plan_line}아래로 대체해보세요.\n\n"
        f"{listed}\n\n"
        f"⚠️ 주의: {info.caution}"
    )
    return append_disclaimer(body)


# ═══════════════════════════════════════════════════════════════════
# 3) 회복 루틴 — active-recovery.ts 이식
# ═══════════════════════════════════════════════════════════════════


@dataclass
class RecoverySession:
    title: str
    duration: str
    steps: list[str]


RECOVERY_SESSIONS: dict[str, RecoverySession] = {
    "light": RecoverySession(
        title="🟢 가벼운 회복 (15분)",
        duration="15분",
        steps=[
            "천천히 걷기 5분 (심박 100~110)",
            "정적 스트레칭 5분 (햄스트링·둔근·종아리)",
            "호흡 명상 5분 (4-7-8 호흡법)",
        ],
    ),
    "moderate": RecoverySession(
        title="🟡 중강도 액티브 회복 (30분)",
        duration="30분",
        steps=[
            "바이크 또는 산책 15분 (심박 120~130, 대화 가능한 강도)",
            "폼롤러 10분 (햄스트링·대퇴사두·등 등 큰 근육군)",
            "가동성 운동 5분 (Cat-Cow, Hip Circle, World's Greatest Stretch)",
        ],
    ),
    "full": RecoverySession(
        title="🔵 풀 회복 세션 (60분)",
        duration="60분",
        steps=[
            "바이크 또는 수영 30분 (Zone 2, 최대심박의 65~70%)",
            "폼롤러 + 마사지볼 15분 (트리거 포인트 위주)",
            "정적 스트레칭 10분 (자세별 30~60초 유지)",
            "사우나 또는 냉수 샤워 5분 (선택)",
        ],
    ),
}

RECOVERY_ALIASES = {
    "가벼운": "light",
    "가볍게": "light",
    "저강도": "light",
    "라이트": "light",
    "보통": "moderate",
    "중강도": "moderate",
    "중간": "moderate",
    "강한": "full",
    "고강도": "full",
    "풀": "full",
    "전체": "full",
}


def normalize_intensity(intensity: str) -> Optional[str]:
    key = (intensity or "").strip().lower()
    if key in RECOVERY_SESSIONS:
        return key
    return RECOVERY_ALIASES.get(key)


def build_recovery_response(intensity: str) -> str:
    key = normalize_intensity(intensity)
    if key is None:
        body = (
            f"⚠️ '{intensity}'는 지원하지 않는 강도예요.\n\n"
            "다음 중 하나로 다시 요청해주세요:\n"
            "- light (가벼운 회복, 15분)\n"
            "- moderate (중강도 액티브 회복, 30분)\n"
            "- full (풀 회복 세션, 60분)"
        )
        return append_disclaimer(body)

    session = RECOVERY_SESSIONS[key]
    steps_text = "\n".join(f"{i + 1}️⃣ {s}" for i, s in enumerate(session.steps))
    body = (
        f"🧘 {session.title}\n\n"
        f"{steps_text}\n\n"
        "💡 핵심: 심박은 130 이하로 유지하고, 통증 없는 가동범위 안에서만 움직이세요.\n"
        "🔥 회복일은 훈련만큼 중요합니다 — 다음 성과는 여기서 만들어져요."
    )
    return append_disclaimer(body)


# ═══════════════════════════════════════════════════════════════════
# 4) 오늘의 운동 플랜 — daily-plan.ts 구성 로직(무상태화) 참고
# ═══════════════════════════════════════════════════════════════════

GOAL_ALIASES = {
    "근력": "strength", "근력강화": "strength", "힘": "strength", "strength": "strength",
    "체지방감량": "fat_loss", "다이어트": "fat_loss", "감량": "fat_loss", "체중감량": "fat_loss",
    "지방감량": "fat_loss", "fat_loss": "fat_loss", "weight_loss": "fat_loss",
    "근비대": "hypertrophy", "벌크업": "hypertrophy", "근육량": "hypertrophy", "hypertrophy": "hypertrophy",
    "체력": "endurance", "지구력": "endurance", "심폐지구력": "endurance", "endurance": "endurance",
    "일반건강": "general", "건강": "general", "general": "general",
}

GOAL_LABEL = {
    "strength": "근력 강화",
    "fat_loss": "체지방 감량",
    "hypertrophy": "근비대",
    "endurance": "체력(지구력) 향상",
    "general": "일반 건강 관리",
}

LEVEL_ALIASES = {
    "입문": "beginner", "초보": "beginner", "beginner": "beginner",
    "중급": "intermediate", "intermediate": "intermediate",
    "상급": "advanced", "고급": "advanced", "advanced": "advanced",
}

LEVEL_LABEL = {"beginner": "입문", "intermediate": "중급", "advanced": "고급"}

# 목표별 본운동 구성 템플릿 — (운동명, 세트x렙 또는 시간, 장비 태그)
# 장비 태그: gym(헬스장 전체) / home(맨몸+최소도구) / none(맨몸만)
MAIN_SETS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "strength": {
        "gym": [
            ("스쿼트", "5세트 x 5회 (고중량)"),
            ("벤치프레스 또는 오버헤드프레스", "5세트 x 5회"),
            ("데드리프트", "3세트 x 5회"),
        ],
        "home": [
            ("불가리안 스플릿 스쿼트 (배낭에 짐 채워 가중)", "4세트 x 8회"),
            ("푸시업 (발 높여 난이도↑)", "4세트 x 최대반복"),
            ("힙 브릿지 (한쪽 다리)", "4세트 x 10회"),
        ],
        "none": [
            ("피스톨 스쿼트 준비동작 (박스 활용)", "4세트 x 8회"),
            ("파이크 푸시업", "4세트 x 최대반복"),
            ("싱글레그 데드리프트", "3세트 x 10회"),
        ],
    },
    "fat_loss": {
        "gym": [
            ("로잉머신 인터벌 (30초 전력/30초 휴식)", "8라운드"),
            ("케틀벨 스윙", "4세트 x 15회"),
            ("스텝업 (박스)", "4세트 x 12회"),
        ],
        "home": [
            ("버피", "4세트 x 12회"),
            ("마운틴 클라이머", "4세트 x 30초"),
            ("점핑 잭", "4세트 x 40초"),
        ],
        "none": [
            ("버피", "4세트 x 10회"),
            ("스쿼트 점프", "4세트 x 12회"),
            ("하이 니 러닝", "4세트 x 30초"),
        ],
    },
    "hypertrophy": {
        "gym": [
            ("레그프레스", "4세트 x 10~12회"),
            ("랫풀다운 또는 풀업", "4세트 x 10회"),
            ("덤벨 숄더프레스", "3세트 x 12회"),
        ],
        "home": [
            ("점프 스쿼트 → 슬로우 스쿼트 (템포 조절)", "4세트 x 12회"),
            ("다이아몬드 푸시업", "4세트 x 최대반복"),
            ("덤벨/물병 로우", "4세트 x 12회"),
        ],
        "none": [
            ("템포 스쿼트 (4초 하강)", "4세트 x 12회"),
            ("디클라인 푸시업", "4세트 x 12회"),
            ("슈퍼맨 로우", "4세트 x 15회"),
        ],
    },
    "endurance": {
        "gym": [
            ("트레드밀 존2 러닝", "25분"),
            ("바이크 인터벌", "10분"),
            ("로잉머신", "10분"),
        ],
        "home": [
            ("계단 오르내리기 또는 제자리 러닝", "20분"),
            ("점핑잭 + 스텝터치 서킷", "10분"),
            ("플랭크 → 걷기 회복 반복", "10분"),
        ],
        "none": [
            ("제자리 조깅", "20분"),
            ("스쿼트-런지 서킷", "10분"),
            ("플랭크 인터벌", "10분"),
        ],
    },
    "general": {
        "gym": [
            ("전신 서킷 (스쿼트·푸시업·로우)", "3세트 x 12회"),
            ("바이크 또는 트레드밀", "15분"),
            ("코어 서킷 (플랭크·데드버그)", "3세트"),
        ],
        "home": [
            ("전신 서킷 (스쿼트·푸시업·플랭크)", "3세트 x 12회"),
            ("빠르게 걷기 또는 계단 오르내리기", "15분"),
            ("코어 루틴", "3세트"),
        ],
        "none": [
            ("맨몸 전신 서킷 (스쿼트·푸시업·플랭크)", "3세트 x 12회"),
            ("제자리 걷기/조깅", "15분"),
            ("코어 루틴 (플랭크·버드독)", "3세트"),
        ],
    },
}

LEVEL_INTENSITY_TIP = {
    "beginner": "처음이라면 위 반복수·시간을 70~80% 강도로 시작해도 충분해요. 완벽한 자세가 무게보다 중요합니다.",
    "intermediate": "이미 익숙하다면 표시된 세트·반복수 그대로 진행하고, 마지막 세트는 실패 직전까지 밀어붙여보세요.",
    "advanced": "표시된 볼륨을 기본으로 하되, 템포 조절(느린 하강)이나 추가 세트로 난이도를 더 올려도 좋습니다.",
}


def _normalize_equipment(equipment: str) -> str:
    key = (equipment or "").strip().lower()
    if key in ("gym", "헬스장", "짐"):
        return "gym"
    if key in ("home", "홈", "집", "홈트"):
        return "home"
    if key in ("none", "맨몸", "무장비", "bodyweight"):
        return "none"
    return "home"


def build_workout_plan(goal: str, level: str = "beginner", minutes: int = 60, equipment: str = "gym") -> str:
    goal_norm = re.sub(r"\s+", "", (goal or "").strip().lower())
    goal_key = GOAL_ALIASES.get(goal_norm, None)
    if goal_key is None:
        options = "、".join(sorted(set(GOAL_LABEL.values())))
        body = (
            f"⚠️ '{goal}' 목표를 인식하지 못했어요.\n\n"
            f"다음 중 하나로 다시 말씀해주세요: {options} "
            "(예: 근력, 체지방 감량, 근비대, 체력, 일반 건강)"
        )
        return append_disclaimer(body)

    level_norm = re.sub(r"\s+", "", (level or "").strip().lower())
    level_key = LEVEL_ALIASES.get(level_norm, "beginner")
    equip_key = _normalize_equipment(equipment)

    try:
        total_minutes = max(10, int(minutes))
    except (TypeError, ValueError):
        total_minutes = 60

    # 워밍업/본운동/쿨다운 시간 배분 (총 시간의 15% / 70% / 15%, 최소값 보정)
    warmup_min = max(5, round(total_minutes * 0.15))
    cooldown_min = max(5, round(total_minutes * 0.15))
    main_min = max(10, total_minutes - warmup_min - cooldown_min)

    main_exercises = MAIN_SETS[goal_key][equip_key]
    equip_label = {"gym": "헬스장", "home": "홈트(최소 도구)", "none": "맨몸"}[equip_key]

    lines = [
        f"🏋️ 오늘의 운동 플랜 — {GOAL_LABEL[goal_key]} / {LEVEL_LABEL[level_key]} / 총 {total_minutes}분 / {equip_label}",
        "",
        f"🔸 워밍업 ({warmup_min}분)",
        "  걷기 또는 가벼운 조깅 + 관절 가동성(어깨 돌리기, 힙 서클, 런지 스트레치)",
        "",
        f"🔸 본운동 ({main_min}분)",
    ]
    for i, (name, volume) in enumerate(main_exercises, start=1):
        lines.append(f"  {i}️⃣ {name} — {volume}")
    lines += [
        "",
        f"🔸 쿨다운 ({cooldown_min}분)",
        "  정적 스트레칭(사용한 주요 근육군 위주) + 호흡 정리",
        "",
        f"💡 {LEVEL_INTENSITY_TIP[level_key]}",
    ]
    return append_disclaimer("\n".join(lines))
