# Import, Export, and Notifications

## Transaction CSV import

The dashboard imports UTF-8 CSV files into one selected account. Imports are
limited to 64 KB and 500 non-empty rows. Every row is validated before the
database transaction starts, so an invalid file saves nothing. A per-user
SHA-256 checksum prevents the exact same file from creating duplicate entries.

Accepted columns are:

- `transaction_date` (or `date`), required in `YYYY-MM-DD` format
- `transaction_type` (or `type`), required as `income`, `expense`, or `transfer`
- `amount`, required and greater than zero
- `description`, `merchant`, `category`, and `notes`, optional

When `category` is supplied, its name and transaction type must match an
available user or shared category. Download the template from the dashboard to
start with the supported header.

API clients send the CSV as the raw `text/csv` request body:

```bash
curl --request POST \
  --header "Authorization: Bearer $FINANCE_ACCESS_TOKEN" \
  --header "Content-Type: text/csv" \
  --data-binary @transactions.csv \
  "http://127.0.0.1:8000/api/v1/import/transactions?account_id=1&source_name=transactions.csv"
```

## Exports

The existing privacy export downloads a complete versioned JSON document.
Transaction CSV export provides spreadsheet-friendly transaction rows with
account and category names. Both exports require the current password. Text
cells beginning with spreadsheet formula characters are prefixed safely in CSV
output to prevent formula execution when the file is opened.

## In-app notifications

Notifications are persisted per user and generated for:

- budget usage reaching at least 80 percent;
- budget spending reaching or exceeding 100 percent;
- savings goal completion;
- generated recurring transactions; and
- completed CSV imports.

Budget and goal notifications use stable deduplication keys. Notifications can
be read, marked all read, or deleted from the dashboard. Turning off
`notification_enabled` in Preferences suppresses future notifications without
removing existing history. This step provides in-app notifications only; email,
SMS, and push delivery require a separately approved delivery provider.
