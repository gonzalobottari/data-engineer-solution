-- Source database schema
-- Note: Contains intentional "bad schema choices" to match real-world messy data

-- Customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),  -- No format enforcement (bad schema choice)
    address TEXT,       -- Unbounded text (bad schema choice)
    ssn VARCHAR(20),    -- Should be fixed length, stored as text (bad schema choice)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP NULL  -- Soft delete support
);

-- Advances (loans) table
CREATE TABLE advances (
    id SERIAL PRIMARY KEY,
    customer_id TEXT NOT NULL,  -- Bad schema: should be INT, stored as TEXT
    amount DECIMAL(12, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, funded, paid_off, declined
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Transactions table (large, mostly historical, rarely changes after insert)
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    advance_id INTEGER NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,  -- payment, disbursement, fee
    created_at TIMESTAMP DEFAULT NOW()
    -- No updated_at: transactions are immutable once created
);

-- Cards table (payment cards belonging to customers)
CREATE TABLE cards (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    card_hash VARCHAR(64) NOT NULL,  -- Hashed card number
    last_four VARCHAR(4) NOT NULL,
    expiry_month INTEGER,
    expiry_year INTEGER,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Customer history (append-only version table)
CREATE TABLE customer_history (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP DEFAULT NOW()
);

-- Scratch table (unused, nobody owns)
CREATE TABLE scratch_temp_data (
    id SERIAL PRIMARY KEY,
    data JSONB,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_updated ON customers(updated_at);
CREATE INDEX idx_advances_customer ON advances(customer_id);
CREATE INDEX idx_advances_updated ON advances(updated_at);
CREATE INDEX idx_transactions_advance ON transactions(advance_id);
CREATE INDEX idx_transactions_created ON transactions(created_at);
CREATE INDEX idx_cards_customer ON cards(customer_id);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER advances_updated_at BEFORE UPDATE ON advances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER cards_updated_at BEFORE UPDATE ON cards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
