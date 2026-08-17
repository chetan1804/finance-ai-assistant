ALTER TABLE recurring_transactions ADD COLUMN schedule_kind TEXT NOT NULL
    DEFAULT 'standard' CHECK(schedule_kind IN ('standard', 'loan_emi'));
ALTER TABLE recurring_transactions ADD COLUMN loan_type TEXT
    CHECK(loan_type IS NULL OR loan_type IN ('home', 'car', 'personal', 'education', 'other'));
ALTER TABLE recurring_transactions ADD COLUMN lender TEXT;

CREATE TABLE investment_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    investment_type TEXT NOT NULL CHECK(investment_type IN (
        'mutual_fund_sip', 'lic', 'rd', 'fd', 'other'
    )),
    name TEXT NOT NULL,
    provider TEXT,
    contribution_amount REAL NOT NULL CHECK(contribution_amount > 0),
    frequency TEXT NOT NULL CHECK(frequency IN (
        'one_time', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'
    )),
    interval_count INTEGER NOT NULL DEFAULT 1 CHECK(interval_count > 0),
    next_date DATE NOT NULL,
    maturity_date DATE,
    total_contributed REAL NOT NULL DEFAULT 0 CHECK(total_contributed >= 0),
    current_value REAL NOT NULL DEFAULT 0 CHECK(current_value >= 0),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'paused', 'completed')),
    last_contribution_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE investment_contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    contribution_date DATE NOT NULL,
    scheduled_for DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (investment_id) REFERENCES investment_plans(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE UNIQUE INDEX investment_scheduled_contribution
    ON investment_contributions(investment_id, scheduled_for)
    WHERE scheduled_for IS NOT NULL;
CREATE INDEX investment_plans_due
    ON investment_plans(user_id, status, next_date);

ALTER TABLE notifications RENAME TO notifications_old;
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    notification_type TEXT NOT NULL CHECK(notification_type IN (
        'budget_warning', 'budget_exceeded', 'goal_completed',
        'recurring_generated', 'import_completed', 'emi_generated',
        'investment_generated', 'investment_maturity'
    )),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0, 1)),
    dedup_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, dedup_key)
);
INSERT INTO notifications
    (id, user_id, notification_type, title, message, is_read, dedup_key, created_at)
SELECT id, user_id, notification_type, title, message, is_read, dedup_key, created_at
FROM notifications_old;
DROP TABLE notifications_old;
CREATE INDEX notifications_inbox
    ON notifications(user_id, is_read, created_at);
