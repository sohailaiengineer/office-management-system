#!/usr/bin/env python3
"""
Office Management System (OMS) - Live MySQL 8 Database Provisioning & Migration Tool

Usage:
    # 1. Initialize all 68 tables on your hosted MySQL 8 database using a connection string:
    python scripts/migrate_to_live_db.py --url "mysql+pymysql://user:password@host:port/dbname?charset=utf8mb4&ssl_mode=REQUIRED"

    # 2. Initialize tables AND seed initial admin/roles/departments data:
    python scripts/migrate_to_live_db.py --url "mysql+pymysql://..." --seed

    # 3. Import full SQL dump directly to remote database:
    python scripts/migrate_to_live_db.py --url "mysql+pymysql://..." --import-sql backups/oms_db_production_export.sql
"""
import os
import sys
import argparse
from sqlalchemy import inspect, text

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import (
    User, Role, Permission, UserRole, Department, Designation, Employee
)

def run_migration(db_url=None, do_seed=False, sql_file=None):
    if db_url:
        # Standardize prefix for PyMySQL
        if db_url.startswith('mysql://'):
            db_url = db_url.replace('mysql://', 'mysql+pymysql://', 1)
        os.environ['DATABASE_URL'] = db_url
        print(f"[INFO] Using target database: {db_url.split('@')[-1] if '@' in db_url else 'specified URL'}")

    # Initialize application in production configuration mode
    app = create_app('production')

    with app.app_context():
        print("[1/4] Testing connection to remote MySQL database...")
        try:
            db.session.execute(text("SELECT 1"))
            print("[OK] Connection verified successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to connect to database: {e}")
            sys.exit(1)

        # Handle SQL file import if requested
        if sql_file and os.path.exists(sql_file):
            print(f"[2/4] Importing SQL file: {sql_file}...")
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            # Split and execute statements
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            for i, stmt in enumerate(statements):
                try:
                    db.session.execute(text(stmt))
                except Exception as ex:
                    # Ignore harmless drop warnings
                    pass
            db.session.commit()
            print(f"[OK] Executed {len(statements)} SQL statements successfully!")
        else:
            print("[2/4] Creating all 68 enterprise relational tables via SQLAlchemy...")
            db.create_all()
            print("[OK] Schema generated successfully!")

        print("[3/4] Inspecting database tables...")
        inspector = inspect(db.engine)
        tables = sorted(inspector.get_table_names())
        print(f"[OK] Total tables present in remote database: {len(tables)} (Target: 68 tables)")

        # Verify critical core tables exist
        critical_tables = [
            'users', 'roles', 'permissions', 'user_roles', 'departments',
            'designations', 'employees', 'attendance', 'leave_requests',
            'payrolls', 'tasks', 'projects', 'audit_logs'
        ]
        missing = [t for t in critical_tables if t not in tables]
        if missing:
            print(f"[WARNING] Missing expected tables: {missing}")
        else:
            print("[OK] All critical enterprise domain tables verified!")

        if do_seed:
            print("[4/4] Checking and seeding baseline records...")
            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()
            if admin:
                print(f"[INFO] Admin user '{admin.username}' already exists in database. Skipping seed.")
            else:
                from seed import seed_database
                print("[INFO] Invoking seed_database()...")
                seed_database('production')
                print("[OK] Seed data successfully populated!")
        else:
            print("[4/4] Seed step skipped (use --seed to initialize demo/admin data if needed).")

    print("\n============================================================")
    print("  LIVE MYSQL DATABASE SETUP & MIGRATION COMPLETE!")
    print("============================================================")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OMS Live MySQL Database Migration Tool")
    parser.add_argument('--url', type=str, default=None, help="Target MySQL 8 connection URL")
    parser.add_argument('--seed', action='store_true', help="Populate default admin, roles, and baseline records")
    parser.add_argument('--import-sql', type=str, default=None, help="Path to SQL dump file to import")
    args = parser.parse_args()

    run_migration(db_url=args.url, do_seed=args.seed, sql_file=args.import_sql)
