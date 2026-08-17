# Loan EMIs and investments

## Loan EMI automation

Create a recurring transaction with `schedule_kind` set to `loan_emi` and a
`loan_type` of `home`, `car`, `personal`, `education`, or `other`. EMI schedules
are always monthly expenses. The server creates or reuses a private `Loan EMI`
expense category and ignores a client-supplied category for the schedule.

Calling `POST /api/v1/recurring-transactions/process` generates every due EMI
through the requested date. Generation is idempotent: running it again cannot
create the same scheduled payment twice. Each generated expense reduces the
selected account balance and is included in expense and savings calculations.

## Investment tracking

Investment plans support mutual-fund SIPs, LIC policies, recurring deposits,
fixed deposits, and other investments. A plan stores its funding account,
contribution amount, frequency, next date, optional maturity date, provider,
and status.

Calling `POST /api/v1/investments/process` records due contributions. A
contribution reduces the funding account balance and increases both total
contributed and current value. It is deliberately not written to the expense
transaction table, so it does not inflate spending. Update current value to
track market movement; gain/loss is current value minus total contributed.

Scheduled generation is idempotent and catches up missed dates, with a safety
limit of 500 contributions per run. Plans can be paused or resumed. One-time
plans and matured schedules are completed automatically.

Both plan details and contribution history are included in password-confirmed
privacy exports and removed by permanent account deletion.
