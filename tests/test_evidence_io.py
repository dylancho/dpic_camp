"""evidence_io — 증거 JSON 파일 읽기.

스키마 위반 항목이 조용히 사라지지 않고 경고로 남는지가 이 테스트의 핵심이다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.proven_scalability.evidence_io import EvidenceFileError, load_evidence

_VALID_ITEM = {
    "criterion_id": "A1_poc_reproducibility",
    "status": "MET",
    "source_tier": 1,
    "source_url": "https://example.com/doc",
    "quote": "PoC 2회 이상 재현",
    "extracted_value": "2회",
}


def _write(tmp_path, payload) -> Path:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_evidence_from_top_level_list(tmp_path):
    path = _write(tmp_path, [_VALID_ITEM])

    evidence, warnings = load_evidence(path)

    assert warnings == []
    assert len(evidence) == 1
    assert evidence[0].criterion_id == "A1_poc_reproducibility"


def test_load_evidence_from_items_key(tmp_path):
    path = _write(tmp_path, {"items": [_VALID_ITEM]})

    evidence, warnings = load_evidence(path)

    assert warnings == []
    assert len(evidence) == 1


def test_missing_file_raises_evidence_file_error(tmp_path):
    missing = tmp_path / "이런파일없음.json"

    with pytest.raises(EvidenceFileError):
        load_evidence(missing)


def test_broken_json_raises_evidence_file_error(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(EvidenceFileError):
        load_evidence(path)


@pytest.mark.parametrize("payload", [42, "그냥 문자열"])
def test_non_list_non_object_top_level_raises(tmp_path, payload):
    path = _write(tmp_path, payload)

    with pytest.raises(EvidenceFileError):
        load_evidence(path)


def test_unknown_criterion_id_is_dropped_but_warned(tmp_path):
    bad_item = {**_VALID_ITEM, "criterion_id": "Z9_no_such_criterion"}
    path = _write(tmp_path, [bad_item])

    evidence, warnings = load_evidence(path)

    assert evidence == []
    assert len(warnings) == 1
    assert "0번" in warnings[0]


def test_out_of_range_source_tier_is_dropped_but_warned(tmp_path):
    bad_item = {**_VALID_ITEM, "source_tier": 9}
    path = _write(tmp_path, [bad_item])

    evidence, warnings = load_evidence(path)

    assert evidence == []
    assert len(warnings) == 1


def test_partial_validity_keeps_valid_items_and_warns_for_the_rest(tmp_path):
    bad_item = {**_VALID_ITEM, "source_tier": 9}
    path = _write(tmp_path, [_VALID_ITEM, bad_item, _VALID_ITEM])

    evidence, warnings = load_evidence(path)

    assert len(evidence) == 2
    assert len(warnings) == 1
    assert "1번" in warnings[0]
