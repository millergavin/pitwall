#!/usr/bin/env python3
"""
Run SQL migration script using psycopg - simple version
"""
import os
import sys
from dotenv import load_dotenv
import psycopg

load_dotenv()

def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=os.getenv('PGPORT', '5433'),
            dbname=os.getenv('PGDATABASE', 'pitwall'),
            user=os.getenv('PGUSER', 'pitwall'),
            password=os.getenv('PGPASSWORD', 'pitwall'),
            connect_timeout=10
        )
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise

def run_migration(script_path: str):
    """Execute SQL migration script."""
    try:
        print(f"Reading migration script: {script_path}")
        with open(script_path, 'r') as f:
            sql = f.read()
        
        print("Connecting to database...")
        conn = get_db_connection()
        conn.autocommit = True
        
        print("Executing migration (this may take a while for large datasets)...")
        with conn.cursor() as cur:
            # Execute the entire script
            cur.execute(sql)
        
        print(f"✓ Successfully executed migration: {script_path}")
        conn.close()
        return True
    except psycopg.errors.DuplicateTable as e:
        print(f"View already exists, dropping and recreating...")
        try:
            conn = get_db_connection()
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("DROP MATERIALIZED VIEW IF EXISTS gold.telemetry_trace CASCADE;")
                print("Dropped existing view, recreating...")
                with open(script_path, 'r') as f:
                    sql = f.read()
                cur.execute(sql)
            print(f"✓ Successfully recreated migration: {script_path}")
            conn.close()
            return True
        except Exception as e2:
            print(f"Error recreating migration: {e2}")
            sys.exit(1)
    except Exception as e:
        print(f"Error executing migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    script_path = sys.argv[1] if len(sys.argv) > 1 else 'init-db/14-create-telemetry-trace-view.sql'
    run_migration(script_path)

