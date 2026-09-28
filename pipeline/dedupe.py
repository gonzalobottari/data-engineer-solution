"""Duplicate customer resolution logic."""
import re
from collections import defaultdict

import duckdb

from config import (
    IDENTITY_FIELDS,
    TEST_EMAIL_PATTERNS,
    TEST_SSN_PATTERNS,
    WAREHOUSE_PATH,
)


def get_warehouse_connection():
    """Connect to DuckDB warehouse."""
    return duckdb.connect(WAREHOUSE_PATH)


def normalize_ssn(ssn):
    """Normalize SSN to digits only for comparison."""
    if not ssn:
        return None
    return re.sub(r"[^0-9]", "", ssn)


def normalize_phone(phone):
    """Normalize phone to digits only."""
    if not phone:
        return None
    return re.sub(r"[^0-9]", "", phone)


def normalize_email(email):
    """Normalize email to lowercase, strip whitespace."""
    if not email:
        return None
    return email.lower().strip()


def is_valid_email(email):
    """Check if email is valid (basic check)."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_phone(phone):
    """Check if phone has 10 digits after normalization."""
    normalized = normalize_phone(phone)
    return normalized and len(normalized) == 10


def is_test_account(customer):
    """Check if this is a test account (should be excluded, not merged)."""
    email = customer.get("email", "") or ""
    ssn = customer.get("ssn", "") or ""

    # Check email patterns
    for pattern in TEST_EMAIL_PATTERNS:
        if pattern in email.lower():
            return True

    # Check SSN patterns
    normalized_ssn = normalize_ssn(ssn)
    for pattern in TEST_SSN_PATTERNS:
        if normalize_ssn(pattern) == normalized_ssn:
            return True

    return False


def has_funded_advance(wh_conn, customer_id):
    """Check if customer has a funded or paid_off advance."""
    result = wh_conn.execute(
        """
        SELECT COUNT(*) FROM advances
        WHERE customer_id = ? AND status IN ('funded', 'paid_off')
        """,
        [str(customer_id)],
    ).fetchone()
    return result[0] > 0


def find_duplicate_groups(wh_conn):
    """
    Find groups of duplicate customers based on IDENTITY fields (SSN).

    SSN is the identity-proving field - exact match means same person.
    Other fields (email, phone, name) only suggest a match but don't prove it.
    """
    # Get all non-deleted, non-test customers
    customers = wh_conn.execute(
        """
        SELECT id, first_name, last_name, email, phone, address, ssn, created_at
        FROM customers
        WHERE deleted_at IS NULL
        ORDER BY id
        """
    ).fetchall()

    columns = ["id", "first_name", "last_name", "email", "phone", "address", "ssn", "created_at"]

    # Group by normalized SSN (identity-proving field)
    ssn_groups = defaultdict(list)
    test_accounts = []

    for row in customers:
        customer = dict(zip(columns, row))

        # Exclude test accounts
        if is_test_account(customer):
            test_accounts.append(customer)
            continue

        normalized_ssn = normalize_ssn(customer["ssn"])
        if normalized_ssn:
            ssn_groups[normalized_ssn].append(customer)

    # Filter to only groups with duplicates
    duplicate_groups = {
        ssn: group for ssn, group in ssn_groups.items() if len(group) > 1
    }

    return duplicate_groups, test_accounts


def select_survivor(wh_conn, group):
    """
    Select which customer record survives from a duplicate group.

    Rules:
    1. Customer with funded/paid_off advance is untouchable - must survive
    2. If multiple have funded advances, flag for manual review (don't merge)
    3. Otherwise, prefer oldest record (lowest ID = first created)
    """
    funded_customers = []
    for customer in group:
        if has_funded_advance(wh_conn, customer["id"]):
            funded_customers.append(customer)

    if len(funded_customers) > 1:
        # Multiple funded customers - cannot automatically merge
        return None, "MANUAL_REVIEW: Multiple customers with funded advances"

    if len(funded_customers) == 1:
        # One funded customer survives
        return funded_customers[0], "Funded advance - untouchable"

    # No funded customers - oldest record survives
    oldest = min(group, key=lambda c: c["id"])
    return oldest, "Oldest record (lowest ID)"


def analyze_duplicates():
    """Analyze duplicate customers and report findings."""
    wh_conn = get_warehouse_connection()

    print("=" * 60)
    print("DUPLICATE CUSTOMER ANALYSIS")
    print("=" * 60)

    duplicate_groups, test_accounts = find_duplicate_groups(wh_conn)

    # Report test accounts
    print(f"\nTest accounts excluded: {len(test_accounts)}")
    for acc in test_accounts:
        print(f"  - ID {acc['id']}: {acc['email']}")

    # Report duplicates
    print(f"\nDuplicate groups found: {len(duplicate_groups)}")

    merge_plan = []

    for ssn, group in duplicate_groups.items():
        print(f"\n--- SSN: {ssn[:3]}**-**-{ssn[-4:]} ({len(group)} records) ---")

        for customer in group:
            funded = has_funded_advance(wh_conn, customer["id"])
            status = " [FUNDED]" if funded else ""
            valid_email = is_valid_email(customer["email"])
            valid_phone = is_valid_phone(customer["phone"])
            email_status = "" if valid_email else " [INVALID EMAIL]"
            phone_status = "" if valid_phone else " [INVALID PHONE]"

            print(
                f"  ID {customer['id']}: {customer['first_name']} {customer['last_name']}"
                f" | {customer['email']}{email_status}"
                f" | {customer['phone']}{phone_status}{status}"
            )

        survivor, reason = select_survivor(wh_conn, group)

        if survivor:
            to_merge = [c for c in group if c["id"] != survivor["id"]]
            print(f"  SURVIVOR: ID {survivor['id']} ({reason})")
            print(f"  TO MERGE: {[c['id'] for c in to_merge]}")
            merge_plan.append(
                {"survivor": survivor, "to_merge": to_merge, "reason": reason}
            )
        else:
            print(f"  ACTION: {reason}")

    wh_conn.close()
    return merge_plan


def analyze_malformed_data():
    """Analyze malformed emails and phones."""
    wh_conn = get_warehouse_connection()

    print("\n" + "=" * 60)
    print("MALFORMED DATA ANALYSIS")
    print("=" * 60)

    customers = wh_conn.execute(
        """
        SELECT id, first_name, last_name, email, phone
        FROM customers
        WHERE deleted_at IS NULL
        """
    ).fetchall()

    invalid_emails = []
    invalid_phones = []
    empty_emails = []
    empty_phones = []

    for row in customers:
        id, first_name, last_name, email, phone = row

        if not email:
            empty_emails.append((id, first_name, last_name))
        elif not is_valid_email(email):
            invalid_emails.append((id, first_name, last_name, email))

        if not phone:
            empty_phones.append((id, first_name, last_name))
        elif not is_valid_phone(phone):
            invalid_phones.append((id, first_name, last_name, phone))

    print(f"\nInvalid emails: {len(invalid_emails)}")
    for id, fn, ln, email in invalid_emails:
        print(f"  ID {id}: {fn} {ln} - '{email}'")

    print(f"\nEmpty emails: {len(empty_emails)}")

    print(f"\nInvalid phones: {len(invalid_phones)}")
    for id, fn, ln, phone in invalid_phones:
        print(f"  ID {id}: {fn} {ln} - '{phone}'")

    print(f"\nEmpty phones: {len(empty_phones)}")

    wh_conn.close()


def execute_merge(merge_plan, dry_run=True):
    """
    Execute the merge plan - reassign cards and mark duplicates as merged.

    In dry_run mode, only prints what would happen.
    """
    wh_conn = get_warehouse_connection()

    print("\n" + "=" * 60)
    print("MERGE EXECUTION" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 60)

    for merge in merge_plan:
        survivor = merge["survivor"]
        to_merge = merge["to_merge"]

        print(f"\nMerging into customer {survivor['id']} ({survivor['first_name']} {survivor['last_name']}):")

        for dup in to_merge:
            print(f"  - Customer {dup['id']}:")

            # Count cards to reassign
            card_count = wh_conn.execute(
                "SELECT COUNT(*) FROM cards WHERE customer_id = ?", [dup["id"]]
            ).fetchone()[0]

            if card_count > 0:
                print(f"    - {card_count} card(s) will be reassigned to customer {survivor['id']}")
                if not dry_run:
                    wh_conn.execute(
                        "UPDATE cards SET customer_id = ? WHERE customer_id = ?",
                        [survivor["id"], dup["id"]],
                    )

            # Mark as merged (soft delete with note)
            print(f"    - Will be marked as merged (soft delete)")
            if not dry_run:
                wh_conn.execute(
                    """
                    UPDATE customers
                    SET deleted_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    [dup["id"]],
                )

    if not dry_run:
        print("\nMerge completed!")
    else:
        print("\nDry run complete. Use --execute to apply changes.")

    wh_conn.close()


def run_dedupe(execute=False):
    """Main entry point for deduplication."""
    merge_plan = analyze_duplicates()
    analyze_malformed_data()

    if merge_plan:
        execute_merge(merge_plan, dry_run=not execute)


if __name__ == "__main__":
    import sys

    execute = "--execute" in sys.argv
    run_dedupe(execute=execute)
