ALTER TABLE transactions ADD COLUMN loan_type TEXT
    CHECK(loan_type IS NULL OR loan_type IN (
        'home', 'car', 'personal', 'education', 'other'
    ));
