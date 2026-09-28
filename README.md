# Fundo Data Engineer Take-Home Solution

An incremental data pipeline that syncs data from an operational database to a warehouse, resolves duplicate customers, and validates data quality.

## Quick Start

```bash
# 1. Start the source database
docker compose up -d

# 2. Wait for database (check it's ready)
docker compose exec source_db pg_isready -U fundo -d fundo_operational

# 3. Install Python dependencies
pip install -r pipeline/requirements.txt

# 4. Run the sync
cd pipeline && python run.py sync

# 5. Run quality checks
python run.py check

# 6. Analyze duplicates
python run.py dedupe
```

Or use the Makefile:

```bash
make start    # Start database
make install  # Install dependencies
make all      # Sync + checks
make dedupe   # Analyze duplicates
```

## Commands

| Command | Description |
|---------|-------------|
| `python run.py sync` | Incremental sync from source to warehouse |
| `python run.py check` | Run data quality checks |
| `python run.py dedupe` | Analyze duplicates (dry run) |
| `python run.py dedupe-exec` | Execute duplicate merge |
| `python run.py all` | Sync + checks |

## Demo: Breaking and Detecting Data Issues

**Show a failing check:**

```bash
# 1. After initial sync, delete a customer from source
make demo-break

# 2. Run checks - they will fail (orphaned data in warehouse)
make check
```

**Fix and recover:**

```bash
# 1. Restore the customer
make demo-fix

# 2. Re-sync and verify
make sync
make check
```

## Project Structure

```
data-engineer-solution/
├── docker-compose.yml      # Source database (PostgreSQL)
├── Makefile                # Convenience commands
├── source_db/
│   ├── init.sql            # Schema definition
│   └── seed.sql            # Test data with duplicates
├── pipeline/
│   ├── requirements.txt    # Python dependencies
│   ├── config.py           # Configuration
│   ├── sync.py             # Incremental sync logic
│   ├── dedupe.py           # Duplicate resolution
│   ├── checks.py           # Data quality checks
│   └── run.py              # CLI entry point
├── warehouse/              # DuckDB warehouse (created at runtime)
├── README.md               # This file
└── SOLUTION.md             # Design decisions
```

## Test Data

The seed data includes:

- **19 customers** with various scenarios
- **3 duplicate groups** (same SSN, different records)
- **3 test accounts** (@fundo.com emails)
- **Malformed data** (invalid emails, phones)
- **1 soft-deleted** customer
- **10 advances** (pending, funded, paid_off, declined)
- **19 transactions**
- **9 cards**

### Duplicate Groups

| SSN | Customer IDs | Notes |
|-----|--------------|-------|
| 123-45-6789 | 1, 4, 5 | Customer 1 has funded advance (survives) |
| 456-78-9012 | 6, 7 | No funded advances (oldest survives) |
| 567-89-0123 | 8, 9 | BOTH have funded advances (manual review) |

## Cleanup

```bash
# Stop database
docker compose down

# Remove warehouse data
make clean

# Full reset
docker compose down -v && make clean
```
