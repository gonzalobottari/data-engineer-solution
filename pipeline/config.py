"""Configuration for the data pipeline."""
import os
from pathlib import Path

# Project root (one level up from pipeline/)
PROJECT_ROOT = Path(__file__).parent.parent

# Source database (PostgreSQL)
SOURCE_DB = {
    "host": os.getenv("SOURCE_HOST", "localhost"),
    "port": int(os.getenv("SOURCE_PORT", "5432")),
    "database": os.getenv("SOURCE_DB", "fundo_operational"),
    "user": os.getenv("SOURCE_USER", "fundo"),
    "password": os.getenv("SOURCE_PASSWORD", "fundo123"),
}

# Warehouse (DuckDB file)
WAREHOUSE_PATH = os.getenv(
    "WAREHOUSE_PATH", str(PROJECT_ROOT / "warehouse" / "fundo_warehouse.duckdb")
)

# Checkpoint file for tracking sync state
CHECKPOINT_PATH = os.getenv(
    "CHECKPOINT_PATH", str(PROJECT_ROOT / "warehouse" / "checkpoint.json")
)

# Tables and their sync strategies
# - "incremental": Use updated_at for change detection
# - "append_only": Only track new inserts (by max ID)
# - "full": Full refresh (for small reference tables)
# - "skip": Don't sync (scratch tables, etc.)
TABLE_STRATEGIES = {
    "customers": "incremental",
    "advances": "incremental",
    "transactions": "append_only",  # Large, immutable after insert
    "cards": "incremental",
    "customer_history": "append_only",  # Append-only by design
    "scratch_temp_data": "skip",  # Unused, don't sync
}

# Fields that PROVE identity (exact match required for deduplication)
IDENTITY_FIELDS = ["ssn"]

# Fields that SUGGEST a match (used for scoring, not proof)
MATCH_SUGGESTING_FIELDS = ["email", "phone", "first_name", "last_name", "address"]

# Test account patterns (to exclude from deduplication)
TEST_EMAIL_PATTERNS = ["@fundo.com"]
TEST_SSN_PATTERNS = ["000-00-0000", "111-11-1111", "222-22-2222"]
