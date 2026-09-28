"""Data quality checks - prove the warehouse is complete and correct."""
import duckdb
import psycopg2

from config import SOURCE_DB, TABLE_STRATEGIES, WAREHOUSE_PATH


def get_source_connection():
    """Connect to source PostgreSQL database."""
    return psycopg2.connect(**SOURCE_DB)


def get_warehouse_connection():
    """Connect to DuckDB warehouse."""
    return duckdb.connect(WAREHOUSE_PATH)


def check_row_counts():
    """Compare row counts between source and warehouse."""
    src_conn = get_source_connection()
    wh_conn = get_warehouse_connection()

    print("=" * 60)
    print("ROW COUNT COMPARISON")
    print("=" * 60)

    src_cur = src_conn.cursor()
    all_pass = True

    for table, strategy in TABLE_STRATEGIES.items():
        if strategy == "skip":
            print(f"\n{table}: SKIPPED (not synced)")
            continue

        # Source count
        src_cur.execute(f"SELECT COUNT(*) FROM {table}")
        src_count = src_cur.fetchone()[0]

        # Warehouse count
        try:
            wh_count = wh_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            wh_count = 0

        status = "PASS" if src_count == wh_count else "FAIL"
        if status == "FAIL":
            all_pass = False

        print(f"\n{table}:")
        print(f"  Source:    {src_count}")
        print(f"  Warehouse: {wh_count}")
        print(f"  Status:    {status}")

    src_conn.close()
    wh_conn.close()

    return all_pass


def check_completeness():
    """Check for missing IDs (gaps) in warehouse."""
    src_conn = get_source_connection()
    wh_conn = get_warehouse_connection()

    print("\n" + "=" * 60)
    print("COMPLETENESS CHECK (Missing IDs)")
    print("=" * 60)

    src_cur = src_conn.cursor()
    all_pass = True

    for table, strategy in TABLE_STRATEGIES.items():
        if strategy == "skip":
            continue

        # Get all IDs from source
        src_cur.execute(f"SELECT id FROM {table} ORDER BY id")
        src_ids = set(row[0] for row in src_cur.fetchall())

        # Get all IDs from warehouse
        try:
            wh_ids = set(
                row[0]
                for row in wh_conn.execute(
                    f"SELECT id FROM {table} ORDER BY id"
                ).fetchall()
            )
        except Exception:
            wh_ids = set()

        # Find gaps
        missing_in_wh = src_ids - wh_ids
        orphaned_in_wh = wh_ids - src_ids

        status = "PASS" if not missing_in_wh and not orphaned_in_wh else "FAIL"
        if status == "FAIL":
            all_pass = False

        print(f"\n{table}:")
        print(f"  Missing in warehouse: {len(missing_in_wh)}")
        if missing_in_wh and len(missing_in_wh) <= 10:
            print(f"    IDs: {sorted(missing_in_wh)}")
        print(f"  Orphaned in warehouse: {len(orphaned_in_wh)}")
        if orphaned_in_wh and len(orphaned_in_wh) <= 10:
            print(f"    IDs: {sorted(orphaned_in_wh)}")
        print(f"  Status: {status}")

    src_conn.close()
    wh_conn.close()

    return all_pass


def check_data_integrity():
    """Check referential integrity in warehouse."""
    wh_conn = get_warehouse_connection()

    print("\n" + "=" * 60)
    print("REFERENTIAL INTEGRITY CHECK")
    print("=" * 60)

    all_pass = True

    # Check advances -> customers
    try:
        orphan_advances = wh_conn.execute(
            """
            SELECT a.id, a.customer_id
            FROM advances a
            LEFT JOIN customers c ON CAST(a.customer_id AS INTEGER) = c.id
            WHERE c.id IS NULL
            """
        ).fetchall()

        print(f"\nAdvances with missing customer:")
        print(f"  Count: {len(orphan_advances)}")
        if orphan_advances:
            all_pass = False
            print(f"  Status: FAIL")
            for adv_id, cust_id in orphan_advances[:5]:
                print(f"    Advance {adv_id} -> Customer {cust_id}")
        else:
            print(f"  Status: PASS")
    except Exception as e:
        print(f"  Error: {e}")
        all_pass = False

    # Check transactions -> advances
    try:
        orphan_txns = wh_conn.execute(
            """
            SELECT t.id, t.advance_id
            FROM transactions t
            LEFT JOIN advances a ON t.advance_id = a.id
            WHERE a.id IS NULL
            """
        ).fetchall()

        print(f"\nTransactions with missing advance:")
        print(f"  Count: {len(orphan_txns)}")
        if orphan_txns:
            all_pass = False
            print(f"  Status: FAIL")
        else:
            print(f"  Status: PASS")
    except Exception as e:
        print(f"  Error: {e}")
        all_pass = False

    # Check cards -> customers
    try:
        orphan_cards = wh_conn.execute(
            """
            SELECT c.id, c.customer_id
            FROM cards c
            LEFT JOIN customers cu ON c.customer_id = cu.id
            WHERE cu.id IS NULL
            """
        ).fetchall()

        print(f"\nCards with missing customer:")
        print(f"  Count: {len(orphan_cards)}")
        if orphan_cards:
            all_pass = False
            print(f"  Status: FAIL")
            for card_id, cust_id in orphan_cards[:5]:
                print(f"    Card {card_id} -> Customer {cust_id}")
        else:
            print(f"  Status: PASS")
    except Exception as e:
        print(f"  Error: {e}")
        all_pass = False

    wh_conn.close()
    return all_pass


def check_data_freshness():
    """Check when data was last synced."""
    wh_conn = get_warehouse_connection()

    print("\n" + "=" * 60)
    print("DATA FRESHNESS CHECK")
    print("=" * 60)

    for table, strategy in TABLE_STRATEGIES.items():
        if strategy == "skip":
            continue

        try:
            result = wh_conn.execute(
                f"SELECT MAX(_synced_at) FROM {table}"
            ).fetchone()
            last_sync = result[0] if result[0] else "Never"
            print(f"\n{table}: Last synced at {last_sync}")
        except Exception:
            print(f"\n{table}: Not yet synced")

    wh_conn.close()


def run_all_checks():
    """Run all data quality checks."""
    print("\n" + "=" * 60)
    print("DATA QUALITY CHECKS")
    print("=" * 60)

    results = []

    results.append(("Row Counts", check_row_counts()))
    results.append(("Completeness", check_completeness()))
    results.append(("Referential Integrity", check_data_integrity()))
    check_data_freshness()  # Info only, no pass/fail

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    print("\n" + "-" * 60)
    if all_pass:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED - Investigation required")

    return all_pass


if __name__ == "__main__":
    run_all_checks()
