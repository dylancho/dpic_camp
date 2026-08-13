"""사용자의 LLM 세션이 만든 증거 JSON을 읽어들인다.

md 지시서(`docs/agent-instructions/`)를 따라 조사한 결과가 이 형식으로 저장되고,
여기서 스키마 검증을 거쳐 채점기로 들어간다. 검증에 실패한 항목은 조용히 버리지 않고
경고로 남긴다 — 조용히 버리면 '근거 없음'과 구분되지 않는다.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from agents.proven_scalability.schema import Evidence


class EvidenceFileError(Exception):
    """증거 파일을 아예 읽을 수 없을 때."""


def load_evidence(path: Path) -> tuple[list[Evidence], list[str]]:
    """증거 JSON을 읽는다. (유효한 Evidence, 경고) 를 돌려준다."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceFileError(f"증거 파일이 없다: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceFileError(f"증거 파일이 올바른 JSON이 아니다: {path}") from exc

    items = raw.get("items") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise EvidenceFileError(
            "증거 파일의 최상위는 리스트이거나 items 키를 가진 객체여야 한다"
        )

    evidence: list[Evidence] = []
    warnings: list[str] = []
    for index, item in enumerate(items):
        try:
            evidence.append(Evidence.model_validate(item))
        except ValidationError as exc:
            warnings.append(
                f"증거 파일 {index}번 항목을 스키마 위반으로 버렸다 "
                f"({exc.error_count()}건): {_first_error(exc)}"
            )
    return evidence, warnings


def _first_error(exc: ValidationError) -> str:
    first = exc.errors()[0]
    location = ".".join(str(part) for part in first["loc"])
    return f"{location}: {first['msg']}"
