#!/usr/bin/env python3
"""Main entry point for the data pipeline."""
import sys


def print_usage():
    print("""
Fundo Data Pipeline
===================

Usage: python run.py <command>

Commands:
  sync          Run incremental sync from source to warehouse
  dedupe        Analyze duplicate customers (dry run)
  dedupe-exec   Analyze and execute duplicate merge
  check         Run data quality checks
  all           Run sync, then checks

Examples:
  python run.py sync       # Sync data from source to warehouse
  python run.py check      # Verify data quality
  python run.py dedupe     # See what would be deduplicated
  python run.py all        # Full sync + quality checks
""")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "sync":
        from sync import run_sync
        run_sync()

    elif command == "dedupe":
        from dedupe import run_dedupe
        run_dedupe(execute=False)

    elif command == "dedupe-exec":
        from dedupe import run_dedupe
        run_dedupe(execute=True)

    elif command == "check":
        from checks import run_all_checks
        success = run_all_checks()
        sys.exit(0 if success else 1)

    elif command == "all":
        from sync import run_sync
        from checks import run_all_checks

        run_sync()
        print("\n")
        success = run_all_checks()
        sys.exit(0 if success else 1)

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
