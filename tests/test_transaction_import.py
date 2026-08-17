import pytest

from src.services.transaction_import import (
    parse_transaction_csv,
    transactions_to_csv,
)


def test_csv_parser_accepts_supported_aliases_and_utf8():
    rows, checksum = parse_transaction_csv(
        "date,type,amount,description\n2026-08-01,expense,42.50,Café\n".encode()
    )

    assert rows[0]["transaction_date"] == "2026-08-01"
    assert rows[0]["amount"] == 42.5
    assert rows[0]["description"] == "Café"
    assert len(checksum) == 64


def test_csv_parser_reports_row_number_without_returning_partial_data():
    with pytest.raises(ValueError, match="CSV row 3"):
        parse_transaction_csv(
            b"date,type,amount\n2026-08-01,income,100\ninvalid,expense,50\n"
        )


def test_csv_export_neutralizes_formula_cells():
    result = transactions_to_csv([
        {
            "transaction_date": "2026-08-01",
            "transaction_type": "expense",
            "amount": 10,
            "description": "=1+1",
        }
    ])

    assert "'=1+1" in result
