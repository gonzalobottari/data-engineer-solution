# Solution Design

> For the full challenge description, see [CHALLENGE.md](CHALLENGE.md).

## What I Built vs. What I Skipped

### Built

1. **Incremental sync** - Full implementation with two strategies
2. **Duplicate resolution** - Analysis and merge logic with business rules
3. **Data quality checks** - Row counts, completeness, referential integrity

### Skipped

- **Hard deletes detection via full diff** - Would require periodic full scans on large tables. The current solution handles soft deletes via `deleted_at` column. For production, I'd use Change Data Capture (CDC) for true delete detection.
- **Automatic duplicate prevention** - The analysis identifies duplicates; prevention would require application-layer validation or database constraints.

---

## Per-Table Strategy

| Table | Strategy | Why |
|-------|----------|-----|
| `customers` | Incremental (`updated_at`) | Core entity, frequently updated, has soft deletes |
| `advances` | Incremental (`updated_at`) | Status changes over time |
| `transactions` | Append-only (max ID) | Large, immutable after insert. No updates, only new rows. |
| `cards` | Incremental (`updated_at`) | Can be updated (e.g., expiry, primary status) |
| `customer_history` | Append-only (max ID) | Designed as append-only audit log |
| `scratch_temp_data` | Skip | Unused table, no value in syncing |

**Tradeoffs:**

- **Incremental by `updated_at`**: Simple, works if all updates touch the timestamp. Fails silently if an update doesn't set `updated_at`. Used a trigger to ensure this.
- **Append-only by max ID**: Most efficient for immutable data. Cannot detect deletes.
- **Full refresh**: Not implemented but would be appropriate for small reference tables.

---

## Cost Impact

**Before (full copy daily):**
- 1% change rate → 99% wasted transfer
- For 1TB database: ~990GB unnecessary daily transfer

**After (incremental):**
- Only changed rows transferred
- Transactions table (largest): only new rows synced
- Estimated reduction: **~90-95%** of daily transfer volume

**Numbers (measured from test data):**
- Initial sync: 19 customers, 10 advances, 19 transactions
- Subsequent sync with no changes: 0 rows transferred
- This is synthetic data; production would need measurement

---

## Identity Rules for Deduplication

### Identity-Proving Fields (exact match = same person)

- **SSN** - Unique government identifier. Normalized to digits only (handles `123-45-6789` vs `123456789`).

### Match-Suggesting Fields (NOT used for automatic merge)

- Email, phone, name, address - Can be similar for different people (roommates, family, common names). Only used for informational display.

**Why this matters:** Merging on email alone would combine a person who typed their address wrong with a completely different person at that address. SSN is the only field that legally identifies one individual.

---

## Business Rules Implementation

### 1. Funded/Paid-Off Advances = Untouchable

```python
def has_funded_advance(customer_id):
    # Check advances table for status IN ('funded', 'paid_off')
```

A customer with financial history is protected. If they're in a duplicate group:
- **One funded**: That customer survives, others merge into it
- **Multiple funded**: Flagged for manual review (IDs 8 and 9 in test data)

### 2. Test Data Exclusion

Identified by:
- Email domain: `@fundo.com`
- SSN pattern: `000-00-0000`, `111-11-1111`, `222-22-2222`

**Important:** Does NOT match `Testerman` surnames or legitimate company addresses.

### 3. Malformed Phones/Emails

**Decision: Flag but don't fix automatically.**

- Invalid emails: `alice.wong@`, `not-an-email`
- Invalid phones: `555BADBAD`, empty strings

**Reasoning:** Automatic "fixing" could corrupt data. Better to surface these for human review. The deduplication report lists them.

### 4. Cards from Merged Customers

Cards are reassigned to the surviving customer:

```python
UPDATE cards SET customer_id = :survivor_id WHERE customer_id = :merged_id
```

**What could break:** If the merged customer had a different billing address associated with their card, payments might fail. Production would need a notification to the customer.

---

## Data Quality Checks

| Check | What It Validates |
|-------|-------------------|
| Row counts | Source count = Warehouse count per table |
| Completeness | No missing IDs in warehouse |
| Orphaned data | No IDs in warehouse that don't exist in source |
| Referential integrity | advances→customers, transactions→advances, cards→customers |
| Freshness | Last sync timestamp per table |

**Demo of failing check:**
```bash
make demo-break  # Delete customer 17 from source
make check       # Shows orphaned row in warehouse
```

---

## Production Evolution

### Tools I Would Use

- **Debezium or Fivetran** for CDC - Captures all changes including deletes at the database log level
- **dbt** for transformations - SQL-based, version controlled, tested
- **Great Expectations or dbt tests** for data quality
- **Airflow or Dagster** for orchestration

### One-Time vs. Permanent

| Script | Type | Reason |
|--------|------|--------|
| Initial full load | One-time | Only needed once |
| Incremental sync | Permanent | Runs on schedule |
| Duplicate backfill merge | One-time | Cleans existing data |
| Duplicate prevention | Permanent | Application/DB constraint |
| Quality checks | Permanent | Continuous monitoring |

### Delivery Priority

1. **Incremental sync** - Biggest cost impact immediately
2. **Quality checks** - Trust before additional work
3. **Duplicate analysis report** - Understand the scope
4. **Duplicate merge (one-time)** - Clean existing data
5. **Duplicate prevention** - Stop new duplicates

---

## Database Choice Tradeoff

Used **PostgreSQL** instead of SQL Server:
- Simpler Docker setup (no EULA, smaller image)
- Same incremental patterns work identically
- Production migration: change connection string and driver

What would differ with SQL Server:
- Built-in CDC feature (would use instead of `updated_at`)
- `MERGE` statement for upserts
- Temporal tables for history
