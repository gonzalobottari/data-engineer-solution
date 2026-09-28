-- Seed data for source database
-- Contains: duplicates, test accounts, malformed data, and realistic scenarios

-- Regular customers
INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at) VALUES
(1, 'John', 'Smith', 'john.smith@email.com', '555-123-4567', '123 Main St, Boston, MA 02101', '123-45-6789', '2024-01-15 10:00:00', '2024-01-15 10:00:00'),
(2, 'Jane', 'Doe', 'jane.doe@email.com', '555-234-5678', '456 Oak Ave, Austin, TX 78701', '234-56-7890', '2024-02-20 11:00:00', '2024-02-20 11:00:00'),
(3, 'Michael', 'Johnson', 'mjohnson@company.com', '555-345-6789', '789 Pine Rd, Seattle, WA 98101', '345-67-8901', '2024-03-10 09:00:00', '2024-03-10 09:00:00');

-- DUPLICATE GROUP 1: Same person (John Smith), different records
-- One has a FUNDED advance - this is the interesting case
INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at) VALUES
(4, 'John', 'Smith', 'johnsmith@gmail.com', '5551234567', '123 Main Street, Boston, MA', '123-45-6789', '2024-04-01 14:00:00', '2024-04-01 14:00:00'),
(5, 'Jon', 'Smith', 'john.smith@email.com', '555.123.4567', '123 Main St, Boston MA 02101', '123456789', '2024-05-15 16:00:00', '2024-05-15 16:00:00');

-- DUPLICATE GROUP 2: Same person (Sarah Williams), no funded advances
INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at) VALUES
(6, 'Sarah', 'Williams', 'sarah.w@email.com', '555-456-7890', '321 Elm St, Denver, CO 80201', '456-78-9012', '2024-01-20 08:00:00', '2024-01-20 08:00:00'),
(7, 'Sara', 'Williams', 'sarahwilliams@email.com', '5554567890', '321 Elm Street, Denver, CO', '456-78-9012', '2024-03-25 12:00:00', '2024-03-25 12:00:00');

-- DUPLICATE GROUP 3: Both have funded advances (edge case)
INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at) VALUES
(8, 'Robert', 'Brown', 'rbrown@email.com', '555-567-8901', '555 Cedar Ln, Miami, FL 33101', '567-89-0123', '2024-02-01 10:00:00', '2024-02-01 10:00:00'),
(9, 'Bob', 'Brown', 'robert.brown@company.com', '555-567-8901', '555 Cedar Lane, Miami, FL', '567-89-0123', '2024-04-10 15:00:00', '2024-04-10 15:00:00');

-- Test accounts (should be excluded, not merged)
INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at) VALUES
(10, 'Test', 'User', 'test@fundo.com', '000-000-0000', 'Test Address', '000-00-0000', '2024-01-01 00:00:00', '2024-01-01 00:00:00'),
(11, 'QA', 'Tester', 'qa@fundo.com', '000-000-0001', '123 Test St', '111-11-1111', '2024-01-01 00:00:00', '2024-01-01 00:00:00'),
(12, 'Demo', 'Account', 'demo@fundo.com', '000-000-0002', 'Demo Address', '222-22-2222', '2024-01-01 00:00:00', '2024-01-01 00:00:00');

-- Tricky: Real person with "Test" in name (should NOT be excluded)
INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at) VALUES
(13, 'William', 'Testerman', 'w.testerman@realcompany.com', '555-678-9012', '888 Real St, Chicago, IL 60601', '678-90-1234', '2024-03-05 09:00:00', '2024-03-05 09:00:00');

-- Customers with malformed data
INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at) VALUES
(14, 'Alice', 'Wong', 'alice.wong@', '555BADBAD', '999 Maple Dr, Portland, OR 97201', '789-01-2345', '2024-02-15 11:00:00', '2024-02-15 11:00:00'),
(15, 'David', 'Lee', 'not-an-email', '(555) 789 0123', '111 Birch Ave, Phoenix, AZ 85001', '890-12-3456', '2024-04-20 14:00:00', '2024-04-20 14:00:00'),
(16, 'Emily', 'Garcia', 'emily@valid.com', '', '222 Spruce Way, San Diego, CA 92101', '901-23-4567', '2024-05-01 10:00:00', '2024-05-01 10:00:00');

-- More regular customers
INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at) VALUES
(17, 'Chris', 'Martinez', 'chris.m@email.com', '555-890-1234', '333 Walnut Blvd, Atlanta, GA 30301', '012-34-5678', '2024-05-10 08:00:00', '2024-05-10 08:00:00'),
(18, 'Amanda', 'Taylor', 'ataylor@company.com', '555-901-2345', '444 Ash Ct, Nashville, TN 37201', '123-45-0000', '2024-05-20 09:00:00', '2024-05-20 09:00:00');

-- Soft-deleted customer
INSERT INTO customers (id, first_name, last_name, email, phone, address, ssn, created_at, updated_at, deleted_at) VALUES
(19, 'Deleted', 'Customer', 'deleted@email.com', '555-000-0000', 'Gone Address', '999-99-9999', '2024-01-01 00:00:00', '2024-01-01 00:00:00', '2024-06-01 12:00:00');

-- Reset sequence
SELECT setval('customers_id_seq', 20);

-- Advances
INSERT INTO advances (id, customer_id, amount, status, created_at, updated_at) VALUES
-- John Smith (customer 1) has a FUNDED advance - this makes him "untouchable"
(1, '1', 5000.00, 'funded', '2024-01-20 10:00:00', '2024-01-25 14:00:00'),
-- Jane Doe has a paid off advance
(2, '2', 3000.00, 'paid_off', '2024-02-25 11:00:00', '2024-04-01 10:00:00'),
-- Michael has a pending advance
(3, '3', 7500.00, 'pending', '2024-03-15 09:00:00', '2024-03-15 09:00:00'),
-- Duplicate John (customer 4) has a declined advance (not funded, so doesn't protect him)
(4, '4', 2000.00, 'declined', '2024-04-05 14:00:00', '2024-04-06 10:00:00'),
-- Sarah Williams (customer 6) has a pending advance
(5, '6', 4000.00, 'pending', '2024-02-01 08:00:00', '2024-02-01 08:00:00'),
-- Robert Brown (customer 8) has a funded advance
(6, '8', 6000.00, 'funded', '2024-02-10 10:00:00', '2024-02-15 12:00:00'),
-- Bob Brown (customer 9, duplicate of Robert) ALSO has a funded advance - edge case!
(7, '9', 8000.00, 'paid_off', '2024-04-15 15:00:00', '2024-06-01 10:00:00'),
-- Test user advance
(8, '10', 100.00, 'pending', '2024-01-01 00:00:00', '2024-01-01 00:00:00'),
-- Regular customer advances
(9, '17', 2500.00, 'funded', '2024-05-15 08:00:00', '2024-05-20 10:00:00'),
(10, '18', 1500.00, 'pending', '2024-05-25 09:00:00', '2024-05-25 09:00:00');

SELECT setval('advances_id_seq', 11);

-- Transactions (larger volume, mostly historical)
INSERT INTO transactions (id, advance_id, amount, transaction_type, created_at) VALUES
-- Transactions for advance 1 (John Smith - funded)
(1, 1, 5000.00, 'disbursement', '2024-01-25 14:00:00'),
(2, 1, -500.00, 'payment', '2024-02-25 10:00:00'),
(3, 1, -500.00, 'payment', '2024-03-25 10:00:00'),
(4, 1, -50.00, 'fee', '2024-03-25 10:01:00'),
-- Transactions for advance 2 (Jane Doe - paid off)
(5, 2, 3000.00, 'disbursement', '2024-02-25 12:00:00'),
(6, 2, -1000.00, 'payment', '2024-03-01 09:00:00'),
(7, 2, -1000.00, 'payment', '2024-03-15 09:00:00'),
(8, 2, -1000.00, 'payment', '2024-04-01 09:00:00'),
(9, 2, -30.00, 'fee', '2024-04-01 09:01:00'),
-- Transactions for advance 6 (Robert Brown - funded)
(10, 6, 6000.00, 'disbursement', '2024-02-15 12:00:00'),
(11, 6, -600.00, 'payment', '2024-03-15 10:00:00'),
(12, 6, -600.00, 'payment', '2024-04-15 10:00:00'),
-- Transactions for advance 7 (Bob Brown - paid off)
(13, 7, 8000.00, 'disbursement', '2024-04-20 15:00:00'),
(14, 7, -2000.00, 'payment', '2024-05-01 10:00:00'),
(15, 7, -2000.00, 'payment', '2024-05-15 10:00:00'),
(16, 7, -2000.00, 'payment', '2024-05-30 10:00:00'),
(17, 7, -2000.00, 'payment', '2024-06-01 10:00:00'),
-- Transactions for advance 9 (Chris Martinez - funded)
(18, 9, 2500.00, 'disbursement', '2024-05-20 10:00:00'),
(19, 9, -250.00, 'payment', '2024-06-20 10:00:00');

SELECT setval('transactions_id_seq', 20);

-- Cards
INSERT INTO cards (id, customer_id, card_hash, last_four, expiry_month, expiry_year, is_primary, created_at, updated_at) VALUES
(1, 1, 'hash_abc123', '4567', 12, 2025, true, '2024-01-15 10:00:00', '2024-01-15 10:00:00'),
(2, 2, 'hash_def456', '8901', 6, 2026, true, '2024-02-20 11:00:00', '2024-02-20 11:00:00'),
(3, 3, 'hash_ghi789', '2345', 3, 2025, true, '2024-03-10 09:00:00', '2024-03-10 09:00:00'),
-- Duplicate John Smith (customer 4) has his own card
(4, 4, 'hash_jkl012', '6789', 9, 2026, true, '2024-04-01 14:00:00', '2024-04-01 14:00:00'),
-- Sarah Williams
(5, 6, 'hash_mno345', '0123', 1, 2027, true, '2024-01-20 08:00:00', '2024-01-20 08:00:00'),
-- Robert Brown
(6, 8, 'hash_pqr678', '4567', 8, 2025, true, '2024-02-01 10:00:00', '2024-02-01 10:00:00'),
-- Bob Brown (duplicate) has different card
(7, 9, 'hash_stu901', '8901', 4, 2026, true, '2024-04-10 15:00:00', '2024-04-10 15:00:00'),
-- Chris Martinez has two cards
(8, 17, 'hash_vwx234', '2345', 11, 2025, true, '2024-05-10 08:00:00', '2024-05-10 08:00:00'),
(9, 17, 'hash_yza567', '6789', 7, 2026, false, '2024-05-15 08:00:00', '2024-05-15 08:00:00');

SELECT setval('cards_id_seq', 10);

-- Customer history (append-only)
INSERT INTO customer_history (customer_id, field_name, old_value, new_value, changed_at) VALUES
(1, 'address', '120 Main St, Boston, MA 02101', '123 Main St, Boston, MA 02101', '2024-01-16 09:00:00'),
(2, 'phone', '555-234-5670', '555-234-5678', '2024-02-21 10:00:00'),
(3, 'email', 'm.johnson@company.com', 'mjohnson@company.com', '2024-03-11 08:00:00');

-- Scratch table (unused data, nobody owns)
INSERT INTO scratch_temp_data (data, notes, created_at) VALUES
('{"temp": "data1"}', 'Old migration leftovers', '2023-06-01 00:00:00'),
('{"temp": "data2"}', 'Test import that was never cleaned up', '2023-08-15 00:00:00'),
('{"debug": true}', NULL, '2023-12-01 00:00:00');
