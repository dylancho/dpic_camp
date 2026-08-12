# 조사 지시서 — 사용 안내

여기 있는 `.md` 파일들은 **사람이 자기 LLM 세션에 붙여넣어 실행하는 조사 지시서**다.
이 레포의 파이썬 코드는 어떤 LLM API도 호출하지 않는다 — 채점(`scoring.py`)은
결정론적 코드이고, 조사만 사람이 직접 LLM(Claude, ChatGPT 등 아무 세션이나)을 통해
수행한다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `00-evidence-schema.md` | 출력 형식(`evidence.json`)의 정의. 모든 블록 작업에 항상 함께 붙여넣는다 |
| `01-block-a-기술작동증명.md` | (A) 기술 작동 증명 블록의 조사 항목 3개 |
| `02-block-b-해자.md` | (B) 해자 블록의 조사 항목 4개 |
| `03-block-c-scaleup.md` | (C) Scale-up 준비 블록의 조사 항목 3개 |

세 블록 문서는 서로 섞이지 않는다 — 각각 자기 블록의 항목만 담고 있다. 한 번에
한 블록씩 조사하거나, 세 블록을 한 세션에서 순서대로 진행해도 된다.

## 사용 흐름

**1. 자기 LLM 세션에 `00-evidence-schema.md`와 조사할 블록 문서를 붙여넣는다.**

예를 들어 (A) 블록을 조사한다면 `00-evidence-schema.md`와
`01-block-a-기술작동증명.md` 두 파일의 내용을 순서대로 붙여넣는다. 대상 기업명과
(알고 있다면) 적용 아키타입도 함께 알려준다.

```
대상 기업: (기업명)
적용 아키타입: (deep_tech / materials / industrial_hardware / energy_infra /
              recycling / software_ai_robotics 중 하나, 모르면 생략)

[여기에 00-evidence-schema.md 내용]

[여기에 01-block-a-기술작동증명.md 내용]
```

**2. "이 기업을 조사해서 evidence.json을 만들어줘"라고 시킨다.**

모델이 웹 검색 등 자신이 가진 도구로 조사하고, 지시서의 형식에 맞춰 JSON을
생성한다. 다른 블록도 조사하려면 해당 블록 문서로 바꿔서 반복한다 (같은
`evidence.json`에 항목을 이어 붙여도 되고, 블록별로 파일을 나눴다가 나중에
`items` 배열을 합쳐도 된다).

**3. 결과를 `evidence.json`으로 저장한다.**

모델이 출력한 JSON을 그대로 파일로 저장한다. 형식은
`00-evidence-schema.md`의 "파일 형식" 절을 따른다.

**4. 채점 실행.**

```
python -m agents.proven_scalability --company "기업명" --evidence evidence.json
```

`--evidence` 없이 실행하면 DART 공시에서 자동으로 뽑을 수 있는 항목(B1·B2·B3
일부)만으로 채점하고, 나머지 대부분은 `UNVERIFIABLE`로 남는다. 세 블록을 모두
조사해서 만든 `evidence.json`을 넘기면 더 완전한 결과를 얻는다.

## 참고

- 아키타입을 모르면 생략해도 된다 — 각 블록 문서가 "아키타입 없으면 원칙 원문의
  중립 기준을 쓴다"고 명시하고 있다
- B1·B2·B3는 DART 공시에서도 자동으로 일부 추출될 수 있다. 사람이 조사한
  근거와 겹쳐도 상관없다 — 더 강한 판정(`MET`)이 최종 채택된다
- 모델이 스키마에 없는 `criterion_id`를 만들면 그 항목은 조용히 버려지고 경고만
  남는다. `00-evidence-schema.md`의 10개 ID 표를 벗어나지 않았는지 확인한다
