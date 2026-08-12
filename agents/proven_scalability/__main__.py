"""CLI: python -m agents.proven_scalability --company "기업명" """

from __future__ import annotations

import argparse
import sys

from agents.proven_scalability.agent import evaluate


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="proven-scalability",
        description="pre-IPO 기업의 하우스 원칙 (d) 기술성 25점을 판정한다",
    )
    parser.add_argument("--company", required=True, help="대상 기업명")
    parser.add_argument(
        "--archetype",
        default=None,
        help="PM 에이전트가 내려준 아키타입. 생략하면 uncalibrated로 실행된다",
    )
    parser.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = parser.parse_args()

    try:
        result = evaluate(args.company, archetype=args.archetype)
    except RuntimeError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    print(f"\n{args.company} — Proven Scalability (기술성)")
    print(f"  verdict : {result.verdict}")
    print(f"  점수    : {result.score}/25 (A {result.block_scores.a}/12 · "
          f"B {result.block_scores.b}/8 · C {result.block_scores.c}/5)")
    print(f"  게이트  : {'통과' if not result.gate_failed else f'미충족 {result.gate_failed}'}")
    print(f"  커버리지: {result.evidence_coverage:.0%}")
    print(f"  보정    : {result.calibration.archetype}"
          f"{'' if result.calibration.archetype_injected else ' (미보정)'}"
          f"{' · 임계치 주입됨' if result.calibration.thresholds_injected else ''}")
    if result.calibration.note:
        print(f"  주의    : {result.calibration.note}")

    if result.research_notes:
        # 커버리지 바로 아래가 아니라 여기 두면 묻힌다 — 커버리지 해석을 바꾸는
        # 정보이므로 실사 질문보다 먼저 보여준다.
        print("\n조사 결함 (커버리지를 그대로 읽지 말 것):")
        for note in result.research_notes:
            print(f"  ! {note}")

    if result.diligence_questions:
        print("\n실사에서 확인할 것:")
        for question in result.diligence_questions:
            print(f"  - {question}")

    return 0


if __name__ == "__main__":
    # Windows cp949 콘솔에서 한글·박스문자를 그대로 출력하기 위해 UTF-8로 고정한다.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
