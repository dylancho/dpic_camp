"""DART 규칙 추출기 테스트.

픽스처는 실제 공시(삼성전자·심텍·루닛 사업/분기보고서)를 라이브로 확인해 본뜬 문구다 —
2026-08-13에 실제 rcept_no로 fetch_document를 호출해 아래 두 표 형식을 확인했다:

- '지적재산권 보유현황' 표 (구분/국내특허/해외특허/총계, 행 "등록"·"출원 중"·"합계")
  → 심텍 2025.09 분기보고서에서 그대로 확인됨
- '[연구개발 인력 구성]' 표 (학력별 박사/석사/학사/기타 헤더 + "인원수" 행)
  → 루닛 2025.09 분기보고서에서 그대로 확인됨

반대로 '기술평가'라는 단어는 실제 공시에서 기관명("한국산업기술평가관리원")이나 연구과제명의
일부로 나타났고, 거래소 기술성 평가 등급 문자열로는 한 번도 나타나지 않았다 — 그래서
B1_exchange_tech_grade 규칙은 만들지 않는다. RULES가 B2·B3만 다룬다는 사실 자체를
테스트로 고정해 둔다 (아래 test_only_two_criteria_are_covered).
"""

from __future__ import annotations

import io
import zipfile

import httpx
import pytest

import agents.proven_scalability.tools.dart as dart
from agents.proven_scalability.extractors import dart_rules
from agents.proven_scalability.tools.dart import DartClient

_CORP_XML = (
    "<result><list><corp_code>00126380</corp_code>"
    "<corp_name>테스트기업</corp_name></list></result>"
).encode("utf-8")


def _zip_bytes(filename: str, content: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(filename, content)
    return buf.getvalue()


def _list_json(rows: list[dict]) -> dict:
    if not rows:
        return {"status": "013", "message": "조회된 데이터가 없습니다."}
    return {"status": "000", "message": "정상", "list": rows}


def _row(rcept_no: str = "20250514001001", dt: str = "20250514") -> dict:
    return {
        "corp_name": "테스트기업",
        "report_nm": "분기보고서",
        "rcept_no": rcept_no,
        "rcept_dt": dt,
    }


def _client(
    tmp_path,
    monkeypatch,
    *,
    corp_xml: bytes = _CORP_XML,
    list_rows: list[dict] | None = None,
    doc_text: str = "",
) -> DartClient:
    """corpCode.xml → list.json → document.xml 순으로 응답하는 대역 DartClient."""
    monkeypatch.setattr(dart, "_CACHE", tmp_path / "corp_codes.json")

    rows = _row() and (list_rows if list_rows is not None else [_row()])

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "corpCode" in url:
            return httpx.Response(200, content=_zip_bytes("CORPCODE.xml", corp_xml))
        if "list.json" in url:
            return httpx.Response(200, json=_list_json(rows))
        return httpx.Response(200, content=_zip_bytes("doc.xml", doc_text.encode("utf-8")))

    transport = httpx.MockTransport(handler)
    return DartClient(api_key="test-key", http=httpx.Client(transport=transport))


# --- 픽스처: 실제 공시 문구를 본뜬 최소 HTML ---

_PATENT_TABLE_HIGH = """
<P USERMARK="F-GL11 ">1) 지적재산권 보유현황</P>
<TABLE ACLASS="NORMAL" WIDTH="600" BORDER="1" AFIXTABLE="N">
<TBODY>
<TR><TD>구분</TD><TD>국내특허</TD><TD>해외특허</TD><TD>총계</TD></TR>
<TR><TD>등록</TD><TD ALIGN="RIGHT">141건</TD><TD ALIGN="RIGHT">3건</TD><TD ALIGN="RIGHT">144건</TD></TR>
<TR><TD>출원 중</TD><TD ALIGN="RIGHT">19건</TD><TD ALIGN="RIGHT">0건</TD><TD ALIGN="RIGHT">19건</TD></TR>
<TR><TD>합계</TD><TD ALIGN="RIGHT">160건</TD><TD ALIGN="RIGHT">3건</TD><TD ALIGN="RIGHT">163건</TD></TR>
</TBODY>
</TABLE>
"""

_PATENT_TABLE_LOW = """
<P USERMARK="F-GL11 ">1) 지적재산권 보유현황</P>
<TABLE ACLASS="NORMAL" WIDTH="600" BORDER="1" AFIXTABLE="N">
<TBODY>
<TR><TD>구분</TD><TD>국내특허</TD><TD>해외특허</TD><TD>총계</TD></TR>
<TR><TD>등록</TD><TD ALIGN="RIGHT">1건</TD><TD ALIGN="RIGHT">0건</TD><TD ALIGN="RIGHT">1건</TD></TR>
<TR><TD>출원 중</TD><TD ALIGN="RIGHT">0건</TD><TD ALIGN="RIGHT">0건</TD><TD ALIGN="RIGHT">0건</TD></TR>
</TBODY>
</TABLE>
"""

_RND_TABLE_HIGH = """
<P>당사의 연구개발 인력은 총 184명으로 전체 인력 중 연구개발 인력의 비중은 약 60%입니다.</P>
<TABLE ACLASS="NORMAL" WIDTH="600" BORDER="0" AFIXTABLE="N">
<TBODY><TR><TD COLSPAN="2">[연구개발 인력 구성]</TD></TR></TBODY>
</TABLE>
<TABLE ACLASS="NORMAL" WIDTH="601" BORDER="1" AFIXTABLE="N">
<THEAD><TR><TH>학력</TH><TH>박사</TH><TH>석사</TH><TH>학사</TH><TH>기타</TH></TR></THEAD>
<TBODY><TR><TD>인원수</TD><TD>20</TD><TD>67</TD><TD>90</TD><TD>7</TD></TR></TBODY>
</TABLE>
"""

_RND_TABLE_LOW = """
<P>당사의 연구개발 인력 현황은 다음과 같습니다.</P>
<TABLE ACLASS="NORMAL" WIDTH="601" BORDER="1" AFIXTABLE="N">
<THEAD><TR><TH>학력</TH><TH>박사</TH><TH>석사</TH><TH>학사</TH><TH>기타</TH></TR></THEAD>
<TBODY><TR><TD>인원수</TD><TD>1</TD><TD>2</TD><TD>7</TD><TD>0</TD></TR></TBODY>
</TABLE>
"""

# 실제 삼성전자 사업보고서(20250311001085)에서 확인된, 표가 아닌 서술형 지적재산권 문단.
# 우리 규칙이 다루는 템플릿(표)과 다르므로 매치되지 않는 게 맞는다 — 추측 금지 원칙의 핵심 사례.
_NARRATIVE_ONLY_IPR = """
<P USERMARK="F-14 B">가. 지적재산권 관련</P>
<P>당사는 R&amp;D 활동의 지적재산화에도 집중하여 1984년 최초로 미국에 특허를 등록한이래
현재 세계적으로 총 <SPAN>265,410건</SPAN>의 특허를 보유하고 있으며,
특히 미국에서의 분쟁에 효과적으로 대응하고자 미국에서 가장 많은 특허를 보유하고 있습니다.</P>
"""

# 실제 루닛 보고서에서 확인된, "기술평가"가 등급이 아니라 기관명·과제명 일부로 등장하는 문구.
_TECH_GRADE_LOOKALIKE = """
<P>당사는 디지털 인공지능(AI) 영상 진단 보조 혁신의료 기술평가를 위한 탐색 과제를
한국산업기술평가관리원과 함께 수행하였다.</P>
"""


def test_patent_table_produces_met_evidence_with_tier_one(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, doc_text=_PATENT_TABLE_HIGH)

    evidence, warnings = dart_rules.extract(client, "테스트기업")

    assert len(evidence) == 1
    item = evidence[0]
    assert item.criterion_id == "B2_registered_patents"
    assert item.status == "MET"
    assert item.source_tier == 1
    assert "144" in item.extracted_value
    assert "20250514001001" in item.source_url
    assert "등록" in item.quote and "144건" in item.quote
    assert warnings == []


def test_low_patent_count_produces_not_met_not_unverifiable(tmp_path, monkeypatch):
    """숫자를 확실히 읽었고 임계치(3건) 미달이면 NOT_MET을 내도 된다 — 추측이 아니라 판독이다."""
    client = _client(tmp_path, monkeypatch, doc_text=_PATENT_TABLE_LOW)

    evidence, _ = dart_rules.extract(client, "테스트기업")

    assert len(evidence) == 1
    assert evidence[0].status == "NOT_MET"
    assert "1" in evidence[0].extracted_value


def test_rnd_personnel_table_computes_advanced_degree_ratio(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, doc_text=_RND_TABLE_HIGH)

    evidence, warnings = dart_rules.extract(client, "테스트기업")

    ids = {e.criterion_id for e in evidence}
    assert "B3_domain_expertise" in ids
    item = next(e for e in evidence if e.criterion_id == "B3_domain_expertise")
    # (박사 20 + 석사 67) / 184 = 47.28...% → 60% 미달이므로 NOT_MET
    assert item.status == "NOT_MET"
    assert "47" in item.extracted_value
    assert item.source_tier == 1
    assert warnings == []


def test_rnd_personnel_table_meets_threshold_when_ratio_high(tmp_path, monkeypatch):
    table = _RND_TABLE_HIGH.replace(
        "<TD>인원수</TD><TD>20</TD><TD>67</TD><TD>90</TD><TD>7</TD>",
        "<TD>인원수</TD><TD>50</TD><TD>50</TD><TD>10</TD><TD>0</TD>",
    )
    client = _client(tmp_path, monkeypatch, doc_text=table)

    evidence, _ = dart_rules.extract(client, "테스트기업")

    item = next(e for e in evidence if e.criterion_id == "B3_domain_expertise")
    assert item.status == "MET"
    assert "90" in item.extracted_value  # (50+50)/110 = 90.9%


def test_low_rnd_ratio_table_still_produces_confident_not_met(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, doc_text=_RND_TABLE_LOW)

    evidence, _ = dart_rules.extract(client, "테스트기업")

    item = next(e for e in evidence if e.criterion_id == "B3_domain_expertise")
    assert item.status == "NOT_MET"


def test_narrative_paragraph_without_table_produces_no_evidence_but_a_warning(
    tmp_path, monkeypatch
):
    """숫자는 있지만 우리가 다루는 표 형식이 아니다 — 추측해서 만들어내지 않는다."""
    client = _client(tmp_path, monkeypatch, doc_text=_NARRATIVE_ONLY_IPR)

    evidence, warnings = dart_rules.extract(client, "테스트기업")

    assert evidence == []
    assert any("건너뛴다" in w or "읽지 못했다" in w for w in warnings)


def test_document_with_no_matching_keywords_produces_no_evidence_and_no_false_warning(
    tmp_path, monkeypatch
):
    """키워드 자체가 없는 문서는 '읽지 못했다' 경고를 낼 이유가 없다 — 그냥 없는 것이다."""
    client = _client(tmp_path, monkeypatch, doc_text="<P>관련 없는 내용입니다.</P>")

    evidence, warnings = dart_rules.extract(client, "테스트기업")

    assert evidence == []
    assert not any("읽지 못했다" in w for w in warnings)


def test_tech_grade_lookalike_text_never_produces_b1_evidence(tmp_path, monkeypatch):
    """'기술평가'라는 단어가 등급이 아니라 기관명·과제명으로 나와도 B1은 만들지 않는다."""
    client = _client(tmp_path, monkeypatch, doc_text=_TECH_GRADE_LOOKALIKE)

    evidence, _ = dart_rules.extract(client, "테스트기업")

    assert not any(e.criterion_id == "B1_exchange_tech_grade" for e in evidence)


def test_only_two_criteria_are_covered_by_any_rule():
    """B1과 A1 등 나머지 항목은 RULES 자체에 없다 — 어떤 입력에도 생길 수 없다."""
    covered = {rule.criterion_id for rule in dart_rules.RULES}
    assert covered == {"B2_registered_patents", "B3_domain_expertise"}


def test_company_not_found_produces_no_evidence_and_a_warning(tmp_path, monkeypatch):
    empty_xml = b"<result></result>"
    client = _client(tmp_path, monkeypatch, corp_xml=empty_xml, doc_text="")

    evidence, warnings = dart_rules.extract(client, "존재하지않는회사")

    assert evidence == []
    assert any("찾지 못했다" in w for w in warnings)


def test_no_disclosures_produces_no_evidence_and_a_warning(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, list_rows=[], doc_text="")

    evidence, warnings = dart_rules.extract(client, "테스트기업")

    assert evidence == []
    assert any("공시" in w and "없" in w for w in warnings)


def test_ambiguous_company_name_skips_extraction_rather_than_guessing(tmp_path, monkeypatch):
    """법인이 여럿으로 갈리면 규칙이 몰래 하나를 고르지 않는다 — dart_search와 같은 원칙."""
    multi_xml = (
        "<result>"
        "<list><corp_code>00000001</corp_code><corp_name>심텍홀딩스</corp_name></list>"
        "<list><corp_code>00000002</corp_code><corp_name>심텍글로벌</corp_name></list>"
        "</result>"
    ).encode("utf-8")
    client = _client(tmp_path, monkeypatch, corp_xml=multi_xml, doc_text=_PATENT_TABLE_HIGH)

    evidence, warnings = dart_rules.extract(client, "심텍")

    assert evidence == []
    assert any("확정" in w or "후보" in w for w in warnings)


def test_all_evidence_has_dart_viewer_source_url(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, doc_text=_PATENT_TABLE_HIGH + _RND_TABLE_HIGH)

    evidence, _ = dart_rules.extract(client, "테스트기업")

    assert evidence
    for item in evidence:
        assert item.source_url.startswith("https://dart.fss.or.kr/dsaf001/main.do?rcpNo=")


@pytest.mark.live
def test_live_dart_patent_rule_against_simtech():
    """실제 심텍 공시로 B2 규칙을 확인한다. `pytest -m live`로만 실행된다."""
    import os

    from dotenv import load_dotenv

    load_dotenv()
    key = os.environ.get("DART_API_KEY")
    if not key:
        pytest.skip("DART_API_KEY 미설정")
    client = DartClient(api_key=key)
    evidence, warnings = dart_rules.extract(client, "심텍")
    assert any(e.criterion_id == "B2_registered_patents" for e in evidence) or warnings
