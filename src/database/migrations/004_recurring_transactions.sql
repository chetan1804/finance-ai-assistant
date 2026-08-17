CREATE TABLE recurring_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    category_id INTEGER,
    transaction_type TEXT NOT NULL
        CHECK(transaction_type IN ('income', 'expense')),
    amount REAL NOT NULL CHECK(amount > 0),
    description TEXT,
    merchant TEXT,
    notes TEXT,
    frequency TEXT NOT NULL
        CHECK(frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
    interval_count INTEGER NOT NULL DEFAULT 1 CHECK(interval_count > 0),
    next_date DATE NOT NULL,
    end_date DATE,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    last_generated_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

ALTER TABLE transactions ADD COLUMN recurring_transaction_id INTEGER
    REFERENCES recurring_transactions(id);
ALTER TABLE transactions ADD COLUMN scheduled_for DATE;

CREATE UNIQUE INDEX recurring_transaction_occurrence
    ON transactions(recurring_transaction_id, scheduled_for)
    WHERE recurring_transaction_id IS NOT NULL;

CREATE INDEX recurring_transactions_due
    ON recurring_transactions(user_id, is_active, next_date);
