#!/usr/bin/env python3
"""
Database initialization script for Ensalamento FUP.

Usage:
    python init_db.py --init        # Create tables
    python init_db.py --seed        # Seed with mock data
    python init_db.py --drop        # Drop all tables
    python init_db.py --reset       # Drop and recreate
    python init_db.py --all         # Drop, create, and seed (full reset)
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db.migrations import init_db, drop_db, seed_db
from src.config.database import get_db_session
from src.models.academic import Usuario


def check_admin_users():
    """Check if admin users exist in database."""
    print("\n📋 Checking admin users...")
    with get_db_session() as session:
        admins = session.query(Usuario).filter(Usuario.role == "admin").all()
        print(f"  Found {len(admins)} admin users:")


def main():
    parser = argparse.ArgumentParser(
        description="Database initialization for Ensalamento FUP"
    )
    parser.add_argument("--init", action="store_true", help="Create database tables")
    parser.add_argument(
        "--seed", action="store_true", help="Seed database with initial data"
    )
    parser.add_argument("--drop", action="store_true", help="Drop all database tables")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables and recreate them",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Full reset: drop, create tables, and seed",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run SQL migrations located in src/db/migrations/",
    )

    args = parser.parse_args()

    # If no arguments, show help
    if not any([args.init, args.seed, args.drop, args.reset, args.all, args.migrate]):
        parser.print_help()
        return

    try:
        if args.drop or args.reset or args.all:
            drop_db()

        if args.init or args.reset or args.all:
            init_db()

        if args.seed or args.all:
            seed_db()

        if args.migrate or args.all:
            # run SQL migrations in src/db/migrations/
            from src.db.migrations import run_sql_migrations

            run_sql_migrations(str(Path(__file__).parent / "src" / "db" / "migrations"))

        # Show admin users if they should exist
        if not args.drop and (args.init or args.all or args.seed):
            check_admin_users()

        print("\n✅ Database initialization completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during database initialization: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
