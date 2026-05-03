from pathlib import Path


def test_required_source_contract_docs_exist() -> None:
    docs = [
        "2026-04-28__source-contract__current__source-contract.md",
        "2026-04-28__source-contract__current__source-endpoint-matrix.md",
        "2026-04-28__source-contract__current__source-field-aliases.md",
        "2026-04-28__source-contract__current__source-anomalies.md",
        "2026-04-28__contract__current__catalog-builder-contract.md",
        "2026-04-28__contract__current__filtering-contract.md",
        "2026-04-28__contract__current__field-coverage-contract.md",
        "2026-04-28__contract__current__db-schema-contract.md",
    ]
    for doc in docs:
        assert Path("docs", doc).exists(), doc


def test_endpoint_matrix_documents_test_detail() -> None:
    text = Path(
        "docs/2026-04-28__source-contract__current__source-endpoint-matrix.md"
    ).read_text(encoding="utf-8")
    assert "get-test-detail/{test_no}" in text


def test_anomalies_document_summary_link_rule() -> None:
    text = Path(
        "docs/2026-04-28__source-contract__current__source-anomalies.md"
    ).read_text(encoding="utf-8")
    assert "barrierInformation" in text
    assert "endpoint templates" in text
