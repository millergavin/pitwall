#!/usr/bin/env python3
"""
Run SQL migration script using psycopg
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
            password=os.getenv('PGPASSWORD', 'pitwall')
        )
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise

def run_migration(script_path: str):
    """Execute SQL migration script."""
    try:
        with open(script_path, 'r') as f:
            sql = f.read()
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
        
        print(f"Successfully executed migration: {script_path}")
        conn.close()
    except Exception as e:
        print(f"Error executing migration: {e}")
        sys.exit(1)

if __name__ == '__main__':
    script_path = sys.argv[1] if len(sys.argv) > 1 else 'init-db/14-create-telemetry-trace-view.sql'
    run_migration(script_path)

