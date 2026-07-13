# ai-fit-trainer — 카카오 PlayMCP 제출용 MCP 서버

AI 피트니스 트레이너 코칭 규칙을 이식한 Python MCP 서버. 코칭 케이스 감지, 부위별
대체 운동, 강도별 회복 루틴, 목표 기반 오늘의 운동 플랜을 외부 API 의존 없이
순수 규칙 엔진만으로 무상태 동작한다.

## 개요

- 서버 이름: `ai-fit-trainer`
- Transport: **Streamable HTTP** (PlayMCP 요구사항) — 엔드포인트 `/mcp`
- 바인드: `0.0.0.0`, 포트: 환경변수 `PORT` (기본값 `8080`)
- 외부 API 호출 없음, DB 없음, 완전 무상태 — 매 요청 순수 함수로만 응답

## 도구 4종

| 도구 | 설명 | 핵심 입력 |
|---|---|---|
| `coach_advice` | 고민/상태 텍스트에서 6가지 케이스(부상·정체기·식단 거부감·타인 비교·피로·입문 막막함)를 감지해 코칭 원칙+구체 조언 반환 | `message: str` |
| `substitute_exercise` | 통증/불편 부위(무릎·허리·어깨·발목)에 맞춰 부담을 줄인 대체 운동 3종 + 주의사항 반환 | `pain_area: str`, `planned_exercise: str` |
| `recovery_routine` | 강도별(light/moderate/full) 회복 루틴 단계 반환 | `intensity: str` |
| `plan_workout` | 목표·수준·시간·장비 기반 오늘의 운동 플랜(워밍업→본운동→쿨다운) 생성 | `goal: str`, `level: str`, `minutes: int`, `equipment: str` |

모든 도구는 응답 마지막에 고정 disclaimer를 포함한다:

> ⚠️ 본 정보는 일반적인 운동 안내이며, 통증·질환이 있다면 의료 전문가와 상담하세요.

부상(injury) 케이스가 감지되면 "48시간 이상 지속되면 병원 상담" 안전 문구가 추가로 포함된다.

## 규칙 요약

- **coach_advice 6케이스**: injury(부상) / plateau(정체기) / diet_resist(식단 거부감) /
  compare(타인 비교 좌절) / fatigue(피로·번아웃) / onboard_fresh(입문 막막함). 한국어
  키워드 정규식으로 감지하며, 매칭 없으면 일반 격려+구체화 질문 반환.
- **substitute_exercise 지원 부위**: 무릎 / 허리 / 어깨 / 발목 (각 대체 운동 3종 +
  주의사항). 지원하지 않는 부위는 통증 부위 회피 원칙 + 범용 대안 안내로 대체.
- **recovery_routine 강도**: light(15분) / moderate(30분) / full(60분).
- **plan_workout 목표**: strength(근력) / fat_loss(체지방 감량) / hypertrophy(근비대) /
  endurance(체력) / general(일반 건강) × 장비(gym/home/none) 조합별 본운동 3종 세트.
  총 시간을 워밍업 15% / 본운동 70% / 쿨다운 15%로 배분(최소값 보정).

## 파일 구성

```
rules.py        # 코칭 케이스·대체 운동·회복 루틴·운동 플랜 규칙 엔진
server.py       # FastMCP 서버 + 4개 도구 정의 + 엔트리포인트
requirements.txt
Dockerfile
test_client.py  # 공식 MCP Python SDK 클라이언트로 실제 접속 검증
```

## 로컬 실행법

```bash
cd Projects/ai-trainer-playmcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 서버 기동 (기본 포트 8080. 다른 프로세스가 8080을 쓰고 있으면 PORT로 변경)
.venv/bin/python server.py
# 또는: PORT=8092 .venv/bin/python server.py
```

핸드셰이크 curl 확인:

```bash
curl -i -X POST http://127.0.0.1:8080/mcp \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl-test","version":"1.0"}}}'
```

전체 도구 검증 (tools/list + 4개 도구 실제 호출):

```bash
.venv/bin/python test_client.py
```

## Docker 실행법

```bash
docker build -t ai-fit-trainer .
docker run --rm -p 8080:8080 -e PORT=8080 ai-fit-trainer
```

비루트 유저(`appuser`)로 실행되며, `python:3.12-slim` 베이스 + 고정 버전 `requirements.txt`.

## PlayMCP 등록 시 endpoint 형식

카카오클라우드(또는 도메인이 붙은 배포 대상)에 올린 뒤, PlayMCP 등록 화면에는 다음 형식으로 입력한다:

```
https://<도메인>/mcp
```

- PlayMCP는 **Streamable HTTP 전송만 지원**한다 — IP 직접 접속이 아닌 **도메인 필수**.
- 로컬 검증에 쓴 포트(8080/PORT)는 배포 환경에 맞게 리버스 프록시/포트포워딩으로 443 → 내부 포트에 연결한다.

## 참고

- 원본 로직(코칭 케이스·대체 운동·회복 루틴)은 사내 봇 코드베이스의 TypeScript 규칙을
  범용 "AI 트레이너" 페르소나로 재작성해 이식했다(특정 코치 인물·채널·텔레그램 명령어
  언급은 모두 제거). `plan_workout`의 워밍업/본운동/쿨다운 시간 배분 로직은 데일리 플랜
  구성 아이디어를 참고해 무상태 규칙으로 새로 작성했다.
