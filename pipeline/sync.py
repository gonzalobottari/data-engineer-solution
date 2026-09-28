"""Incremental sync from source to warehouse."""
import json
import os
from datetime import datetime
from pathlib import Path

import duckdb
import psycopg2

from config import (
    CHECKPOINT_PATH,
    SOURCE_DB,
    TABLE_STRATEGIES,
    WAREHOUSE_PATH,
)


def get_source_connection():
    """Connect to source PostgreSQL database."""
    return psycopg2.connect(**SOURCE_DB)


def get_warehouse_connection():
    """Connect to DuckDB warehouse."""
    Path(WAREHOUSE_PATH).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(WAREHOUSE_PATH)


def load_checkpoint():
    """Load sync checkpoint from file."""
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    return {}


def save_checkpoint(checkpoint):
    """Save sync checkpoint to file."""
    Path(CHECKPOINT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(checkpoint, f, indent=2, default=str)


def init_warehouse_schema(wh_conn):
    """Create warehouse tables if they don't exist."""
    wh_conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            first_name VARCHAR,
            last_name VARCHAR,
            email VARCHAR,
            phone VARCHAR,
            address VARCHAR,
            ssn VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            deleted_at TIMESTAMP,
            _synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    wh_conn.execute("""
        CREATE TABLE IF NOT EXISTS advances (
            id INTEGER PRIMARY KEY,
            customer_id VARCHAR,
            amount DECIMAL(12, 2),
            status VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            _synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    wh_conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            advance_id INTEGER,
            amount DECIMAL(12, 2),
            transaction_type VARCHAR,
            created_at TIMESTAMP,
            _synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    wh_conn.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            card_hash VARCHAR,
            last_four VARCHAR,
            expiry_month INTEGER,
            expiry_year INTEGER,
            is_primary BOOLEAN,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            _synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    wh_conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_history (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            field_name VARCHAR,
            old_value VARCHAR,
            new_value VARCHAR,
            changed_at TIMESTAMP,
            _synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def sync_incremental(src_conn, wh_conn, table, checkpoint):
    """Sync table using updated_at for change detection."""
    last_sync = checkpoint.get(table, {}).get("last_updated_at")

    cur = src_conn.cursor()

    # Get column names
    cur.execute(f"SELECT * FROM {table} LIMIT 0")
    columns = [desc[0] for desc in cur.description]

    # Fetch changed rows
    if last_sync:
        cur.execute(
            f"SELECT * FROM {table} WHERE updated_at > %s ORDER BY updated_at",
            (last_sync,),
        )
    else:
        cur.execute(f"SELECT * FROM {table} ORDER BY updated_at")

    rows = cur.fetchall()
    if not rows:
        print(f"  {table}: no changes")
        return checkpoint

    # Upsert into warehouse
    placeholders = ", ".join(["?"] * len(columns))
    col_list = ", ".join(columns)
    update_cols = ", ".join([f"{c} = EXCLUDED.{c}" for c in columns if c != "id"])
    now = datetime.now()

    for row in rows:
        wh_conn.execute(
            f"""
            INSERT INTO {table} ({col_list}, _synced_at)
            VALUES ({placeholders}, ?)
            ON CONFLICT (id) DO UPDATE SET {update_cols}, _synced_at = ?
            """,
            list(row) + [now, now],
        )

    # Update checkpoint with max updated_at from fetched rows
    max_updated = max(r[columns.index("updated_at")] for r in rows)
    checkpoint[table] = {"last_updated_at": max_updated.isoformat()}

    print(f"  {table}: synced {len(rows)} rows")
    return checkpoint


def sync_append_only(src_conn, wh_conn, table, checkpoint):
    """Sync table by tracking max ID (for immutable/append-only tables)."""
    last_id = checkpoint.get(table, {}).get("last_id", 0)

    cur = src_conn.cursor()

    # Get column names
    cur.execute(f"SELECT * FROM {table} LIMIT 0")
    columns = [desc[0] for desc in cur.description]

    # Fetch new rows only
    cur.execute(f"SELECT * FROM {table} WHERE id > %s ORDER BY id", (last_id,))
    rows = cur.fetchall()

    if not rows:
        print(f"  {table}: no new rows")
        return checkpoint

    # Insert into warehouse
    placeholders = ", ".join(["?"] * len(columns))
    col_list = ", ".join(columns)
    now = datetime.now()

    for row in rows:
        wh_conn.execute(
            f"""
            INSERT INTO {table} ({col_list}, _synced_at)
            VALUES ({placeholders}, ?)
            ON CONFLICT (id) DO NOTHING
            """,
            list(row) + [now],
        )

    # Update checkpoint
    max_id = max(r[0] for r in rows)  # id is first column
    checkpoint[table] = {"last_id": max_id}

    print(f"  {table}: inserted {len(rows)} new rows")
    return checkpoint


def detect_deletes(src_conn, wh_conn, table):
    """Detect rows deleted from source (for tables with soft deletes via deleted_at)."""
    # For customers, we handle soft deletes via the deleted_at column
    # which is already synced via incremental sync
    if table == "customers":
        result = wh_conn.execute(
            "SELECT COUNT(*) FROM customers WHERE deleted_at IS NOT NULL"
        ).fetchone()
        if result[0] > 0:
            print(f"  {table}: {result[0]} soft-deleted records in warehouse")


def run_sync():
    """Run the full sync process."""
    print(f"Starting sync at {datetime.now().isoformat()}")
    print("-" * 50)

    checkpoint = load_checkpoint()
    src_conn = get_source_connection()
    wh_conn = get_warehouse_connection()

    try:
        # Initialize warehouse schema
        init_warehouse_schema(wh_conn)

        # Sync each table according to its strategy
        for table, strategy in TABLE_STRATEGIES.items():
            if strategy == "skip":
                print(f"  {table}: skipped (strategy: skip)")
                continue
            elif strategy == "incremental":
                checkpoint = sync_incremental(src_conn, wh_conn, table, checkpoint)
                detect_deletes(src_conn, wh_conn, table)
            elif strategy == "append_only":
                checkpoint = sync_append_only(src_conn, wh_conn, table, checkpoint)
            elif strategy == "full":
                # Not implemented - would truncate and reload
                print(f"  {table}: full refresh not implemented")

        # Save checkpoint
        save_checkpoint(checkpoint)
        print("-" * 50)
        print("Sync completed successfully")

    finally:
        src_conn.close()
        wh_conn.close()


if __name__ == "__main__":
    run_sync()
