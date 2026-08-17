import csv
import hashlib
import io

from src.security.validation import (
    validate_iso_date,
    validate_money,
    validate_text,
)


MAX_IMPORT_ROWS = 500
MAX_IMPORT_BYTES = 64 * 1024


def parse_transaction_csv(content: bytes):
    if not content:
        raise ValueError("The CSV file is empty.")
    if len(content) > MAX_IMPORT_BYTES:
        raise ValueError("The CSV file must not exceed 64 KB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("The CSV file must use UTF-8 encoding.") from error

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("The CSV file must include a header row.")
    if any(header is None or not header.strip() for header in reader.fieldnames):
        raise ValueError("CSV column names must not be empty.")
    headers = [header.strip().casefold() for header in reader.fieldnames]
    if len(headers) != len(set(headers)):
        raise ValueError("CSV column names must be unique.")
    reader.fieldnames = headers
    date_field = "transaction_date" if "transaction_date" in headers else "date"
    type_field = "transaction_type" if "transaction_type" in headers else "type"
    missing = [name for name in (date_field, type_field, "amount") if name not in headers]
    if missing:
        raise ValueError(f"Missing CSV columns: {', '.join(missing)}.")

    rows = []
    for row_number, raw in enumerate(reader, start=2):
        if row_number > MAX_IMPORT_ROWS + 1:
            raise ValueError(f"A CSV import may contain at most {MAX_IMPORT_ROWS} rows.")
        if None in raw:
            raise ValueError(f"Row {row_number} contains more values than the header.")
        if not any((value or "").strip() for value in raw.values()):
            continue
        try:
            transaction_type = validate_text(
                raw.get(type_field), "transaction_type", max_length=20
            ).casefold()
            if transaction_type not in {"income", "expense", "transfer"}:
                raise ValueError("transaction_type must be income, expense, or transfer.")
            rows.append({
                "transaction_date": validate_iso_date(
                    (raw.get(date_field) or "").strip(),
                    "transaction_date",
                    allow_none=False,
                ),
                "transaction_type": transaction_type,
                "amount": validate_money(float((raw.get("amount") or "").strip())),
                "description": validate_text(
                    raw.get("description"), "description", max_length=500, required=False
                ),
                "merchant": validate_text(
                    raw.get("merchant"), "merchant", max_length=255, required=False
                ),
                "notes": validate_text(
                    raw.get("notes"), "notes", max_length=1000,
                    required=False, allow_newlines=True,
                ),
                "category": validate_text(
                    raw.get("category"), "category", max_length=100, required=False
                ),
            })
        except (TypeError, ValueError) as error:
            raise ValueError(f"CSV row {row_number}: {error}") from error
    if not rows:
        raise ValueError("The CSV file contains no transaction rows.")
    return rows, hashlib.sha256(content).hexdigest()


def safe_spreadsheet_value(value):
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def transactions_to_csv(transactions):
    output = io.StringIO(newline="")
    columns = (
        "transaction_date", "transaction_type", "amount", "description",
        "merchant", "category", "account", "notes",
    )
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for transaction in transactions:
        writer.writerow({
            column: safe_spreadsheet_value(transaction.get(column))
            for column in columns
        })
    return output.getvalue()
