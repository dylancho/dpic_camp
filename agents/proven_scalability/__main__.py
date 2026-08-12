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
          f"{'' if result.calibration.injected else ' (미보정)'}")
    if result.calibration.note:
        print(f"  주의    : {result.calibration.note}")

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
