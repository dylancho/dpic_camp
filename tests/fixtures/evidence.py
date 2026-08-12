from agents.proven_scalability.schema import Evidence, Status


def ev(
    criterion_id: str,
    status: Status = "MET",
    tier: int = 1,
    value: str | None = None,
) -> Evidence:
    """테스트용 Evidence 빌더. 기본은 1급 근거의 MET."""
    return Evidence(
        criterion_id=criterion_id,
        status=status,
        source_tier=tier,
        source_url="https://example.com/doc",
        quote=f"{criterion_id} 관련 인용",
        extracted_value=value,
    )
