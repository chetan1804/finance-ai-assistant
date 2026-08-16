-- Bootstrap-compatible SQLite schema snapshot for unversioned databases.
-- Runtime upgrades and the authoritative latest schema use immutable migrations.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    currency TEXT DEFAULT 'INR' CHECK(length(currency) = 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL,
    institution TEXT,
    balance REAL DEFAULT 0,
    currency TEXT DEFAULT 'INR' CHECK(length(currency) = 3),
    is_active INTEGER DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    category_type TEXT NOT NULL CHECK(category_type IN ('income', 'expense')),
    parent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id),

    FOREIGN KEY (parent_id)
        REFERENCES categories(id)
);


CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    category_id INTEGER,
    transaction_type TEXT NOT NULL
        CHECK(transaction_type IN ('income', 'expense', 'transfer')),
    amount REAL NOT NULL CHECK(amount > 0),
    description TEXT,
    transaction_date DATE NOT NULL,
    merchant TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id),

    FOREIGN KEY (account_id)
        REFERENCES accounts(id),

    FOREIGN KEY (category_id)
        REFERENCES categories(id)
);


CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    period TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id),

    FOREIGN KEY (category_id)
        REFERENCES categories(id)
);


CREATE TABLE IF NOT EXISTS financial_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    target_amount REAL NOT NULL CHECK(target_amount > 0),
    current_amount REAL DEFAULT 0 CHECK(current_amount >= 0),
    target_date DATE,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    language TEXT DEFAULT 'English',
    currency TEXT DEFAULT 'INR' CHECK(length(currency) = 3),
    monthly_income REAL CHECK(monthly_income IS NULL OR monthly_income > 0),
    risk_preference TEXT,
    notification_enabled INTEGER DEFAULT 1
        CHECK(notification_enabled IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
);


CREATE TABLE IF NOT EXISTS user_credentials (
    user_id INTEGER PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS auth_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    access_token_hash TEXT UNIQUE NOT NULL,
    refresh_token_hash TEXT UNIQUE NOT NULL,
    access_expires_at TIMESTAMP NOT NULL,
    refresh_expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_access
    ON auth_sessions(access_token_hash, access_expires_at);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_refresh
    ON auth_sessions(refresh_token_hash, refresh_expires_at);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_active
    ON auth_sessions(user_id, revoked_at, refresh_expires_at);
