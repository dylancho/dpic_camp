from agents.proven_scalability.tools import kipris


def test_patent_search_reports_unavailability_explicitly():
    result = kipris.patent_search(applicant="테스트기업")
    assert "KIPRIS" in result
    # 리서처가 UNVERIFIABLE로 기록하도록 유도하는 문구가 있어야 한다
    assert "확인" in result


def test_patent_search_does_not_claim_zero_patents():
    import re

    # 도구의 능력 부족과 특허의 실제 부재를 엄밀히 구분한다.
    # 허용: "조회할 수 없다" (도구가 조회 불가) — B2를 UNVERIFIABLE로 기록
    # 금지: "특허가 없는" (특허 자체가 없음) — 잘못 해석하면 B2를 NOT_MET으로 기록, 해자 점수 상실
    # 따라서 '특허'를 주어/목어로 하는 부재 표현만 필터링하면 도구 제약은 통과한다.

    result = kipris.patent_search(applicant="테스트기업")

    # 직접 명시된 경우들 (문제를 일으킨 구체 사례)
    assert "0건" not in result
    assert "없습니다" not in result

    # 특허를 주어/목어로 하는 부재 표현 (동사 구의 간섭 없이)
    subject_attached_patterns = [
        r"특허[이가은는을를도]?\s*(?:없|미보유|존재하지\s*않|보유하지\s*않)",  # 특허가 없는, 특허 미보유, 등
        r"등록\s*특허\s*없음",  # 등록 특허 없음
    ]

    for pattern in subject_attached_patterns:
        assert not re.search(pattern, result), f"특허 부재를 주장하는 패턴 '{pattern}' 발견: {result}"

    # 영 개수 표현
    zero_count_patterns = [
        r"0\s*[건개]",  # 0건, 0개, 0 건, 0 개
    ]

    for pattern in zero_count_patterns:
        assert not re.search(pattern, result), f"영 개수를 주장하는 패턴 '{pattern}' 발견: {result}"


def test_patent_search_steers_to_unverifiable():
    # 리서처가 B2를 올바르게 UNVERIFIABLE로 기록하도록 명시적으로 유도해야 한다.
    # 부재 패턴 필터링만으로는 부족하다 — 올바른 스티어링 문구를 빼먹는 리다입도 결국 오류다.

    result = kipris.patent_search(applicant="테스트기업")
    assert "확인 불가" in result or "UNVERIFIABLE" in result
