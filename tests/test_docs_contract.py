from pathlib import Path


def test_required_source_contract_docs_exist() -> None:
    docs = [
        "source_contract.md",
        "source_endpoint_matrix.md",
        "source_field_aliases.md",
        "source_anomalies.md",
        "catalog_builder_contract.md",
        "filtering_contract.md",
        "field_coverage_contract.md",
        "db_schema_contract.md",
    ]
    for doc in docs:
        assert Path("docs", doc).exists(), doc


def test_endpoint_matrix_documents_test_detail() -> None:
    text = Path("docs/source_endpoint_matrix.md").read_text(encoding="utf-8")
    assert "get-test-detail/{test_no}" in text


def test_anomalies_document_summary_link_rule() -> None:
    text = Path("docs/source_anomalies.md").read_text(encoding="utf-8")
    assert "barrierInformation" in text
    assert "endpoint templates" in text
