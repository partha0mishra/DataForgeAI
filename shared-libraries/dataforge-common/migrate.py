#!/usr/bin/env python3
"""Database migration helper script for DataForge AI.

This script provides convenient commands for managing database migrations using Alembic.
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str]) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <command> [args]")
        print("\nCommands:")
        print("  upgrade [revision]   - Upgrade to a later version (default: head)")
        print("  downgrade [revision] - Revert to a previous version")
        print("  current              - Display current revision")
        print("  history              - List changeset scripts in chronological order")
        print("  heads                - Show current available heads")
        print("  revision [message]   - Create a new revision file")
        print("  autogenerate [msg]   - Auto-generate a new revision from model changes")
        print("  stamp [revision]     - 'stamp' the revision table with given revision")
        print("\nExamples:")
        print("  python migrate.py upgrade           # Upgrade to latest")
        print("  python migrate.py downgrade -1      # Downgrade one revision")
        print("  python migrate.py autogenerate 'Add user preferences'")
        sys.exit(1)

    command = sys.argv[1]

    # Change to the script directory
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))

    if command == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        return run_command(["alembic", "upgrade", revision])

    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        return run_command(["alembic", "downgrade", revision])

    elif command == "current":
        return run_command(["alembic", "current"])

    elif command == "history":
        return run_command(["alembic", "history", "--verbose"])

    elif command == "heads":
        return run_command(["alembic", "heads"])

    elif command == "revision":
        message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "New revision"
        return run_command(["alembic", "revision", "-m", message])

    elif command == "autogenerate":
        message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Auto-generated revision"
        return run_command(["alembic", "revision", "--autogenerate", "-m", message])

    elif command == "stamp":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        return run_command(["alembic", "stamp", revision])

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
