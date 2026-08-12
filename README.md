# Proven Scalability 에이전트

드림인베스터클럽 캠프 5조 · pre-IPO 투자 검토 멀티 에이전트의 기술성 축 (25점).

## 설계

- 설계 문서: `docs/specs/2026-08-12-proven-scalability-agent-design.md`
- 구현 계획: `docs/plans/2026-08-12-proven-scalability-agent.md`

증거 수집은 LLM이, 배점과 게이트 판정은 순수 Python이 한다. 같은 증거면 항상 같은 점수가 나온다.

## 설치

```bash
pip install -e ".[dev]"
cp .env.example .env   # DART_API_KEY, ANTHROPIC_API_KEY 를 채운다
```

## 실행

```bash
python -m agents.proven_scalability --company "기업명" --archetype materials
python -m agents.proven_scalability --company "기업명" --json
```

`--archetype`은 PM 에이전트가 내려주는 값이다. 생략하면 아키타입 중립 기준으로 실행되고
결과에 `uncalibrated`로 표시된다 — 이 에이전트는 아키타입을 자체 분류하지 않는다.

아키타입: `deep_tech` · `materials` · `industrial_hardware` · `energy_infra` · `recycling` · `software_ai_robotics`

## 테스트

```bash
python -m pytest              # 네트워크 없이 전부 실행
python -m pytest -m live      # DART 실연결 테스트
```

## 한계

- **KIPRIS 키 미확보** — 등록 특허 건수와 청구항 구조를 조회할 수 없어 `B2_registered_patents`는
  대부분 `UNVERIFIABLE`로 떨어진다. `tools/kipris.py`에 자리를 비워 뒀다
- **(C) Scale-up 기준은 본 설계의 제안** — 하우스 원칙 원문에 세부 기준이 없어 직접 정의했다. 팀 승인 필요
- **`INSUFFICIENT_EVIDENCE`** — 상위 오케스트레이터가 세 값을 받아줄 수 있는지 미확인
