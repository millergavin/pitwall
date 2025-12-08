#!/usr/bin/env python3
"""
Run SQL migration script using psycopg with progress indicators
"""
import os
import sys
import time
from dotenv import load_dotenv
import psycopg
from psycopg import sql

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

def get_table_row_count(conn, schema: str, table: str) -> int:
    """Get row count for a table."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                    sql.Identifier(schema),
                    sql.Identifier(table)
                )
            )
            return cur.fetchone()[0]
    except:
        return 0

def estimate_progress(conn, step: str):
    """Print progress information."""
    print(f"\n[{step}]")
    print("  Checking data volumes...")
    
    try:
        telemetry_count = get_table_row_count(conn, 'silver', 'car_telemetry')
        gps_count = get_table_row_count(conn, 'silver', 'car_gps')
        laps_count = get_table_row_count(conn, 'silver', 'laps')
        
        print(f"  - Telemetry samples: {telemetry_count:,}")
        print(f"  - GPS samples: {gps_count:,}")
        print(f"  - Laps: {laps_count:,}")
        
        if telemetry_count > 0:
            estimated_time = (telemetry_count / 100000) * 60  # Rough estimate: 1 min per 100k rows
            print(f"  - Estimated time: ~{estimated_time:.1f} minutes")
    except Exception as e:
        print(f"  (Could not get counts: {e})")

def run_migration(script_path: str):
    """Execute SQL migration script with progress tracking."""
    try:
        print(f"Reading migration script: {script_path}")
        with open(script_path, 'r') as f:
            sql_content = f.read()
        
        print("Connecting to database...")
        conn = get_db_connection()
        conn.autocommit = True
        
        # Estimate progress
        estimate_progress(conn, "Pre-flight check")
        
        # Check if view exists
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'gold' 
                    AND matviewname = 'telemetry_trace'
                )
            """)
            view_exists = cur.fetchone()[0]
            
            if view_exists:
                print("\n⚠ View already exists. Dropping existing view...")
                cur.execute("DROP MATERIALIZED VIEW IF EXISTS gold.telemetry_trace CASCADE;")
                print("✓ Dropped existing view")
        
        print("\n" + "="*60)
        print("Starting materialized view creation...")
        print("This may take several minutes for large datasets.")
        print("="*60)
        
        start_time = time.time()
        
        # Split into main view creation and indexes
        statements = []
        current_statement = []
        in_create_view = False
        
        for line in sql_content.split('\n'):
            line_stripped = line.strip()
            
            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('--'):
                continue
            
            current_statement.append(line)
            
            # Check if we're starting CREATE MATERIALIZED VIEW
            if 'CREATE MATERIALIZED VIEW' in line.upper():
                in_create_view = True
            
            # Check if we've completed a statement (ends with semicolon)
            if line_stripped.endswith(';') and not in_create_view:
                statements.append('\n'.join(current_statement))
                current_statement = []
            elif line_stripped.endswith(';') and 'ORDER BY' in line.upper():
                # End of CREATE MATERIALIZED VIEW
                statements.append('\n'.join(current_statement))
                current_statement = []
                in_create_view = False
        
        # Add any remaining statement
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        print(f"\nExecuting {len(statements)} SQL statement(s)...")
        
        with conn.cursor() as cur:
            for i, statement in enumerate(statements, 1):
                if not statement.strip():
                    continue
                
                print(f"\n[{i}/{len(statements)}] Executing statement...")
                if 'CREATE MATERIALIZED VIEW' in statement.upper():
                    print("  Creating materialized view (this is the slow part)...")
                elif 'CREATE INDEX' in statement.upper():
                    print("  Creating index...")
                
                statement_start = time.time()
                try:
                    cur.execute(statement)
                    elapsed = time.time() - statement_start
                    print(f"  ✓ Completed in {elapsed:.2f} seconds")
                except Exception as e:
                    elapsed = time.time() - statement_start
                    print(f"  ✗ Error after {elapsed:.2f} seconds: {e}")
                    print(f"  Statement preview: {statement[:200]}...")
                    raise
        
        total_time = time.time() - start_time
        
        print("\n" + "="*60)
        print(f"✓ Successfully executed migration in {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        print("="*60)
        
        # Get final row count - check for both test and production view names
        print("\nFinal view statistics:")
        view_names = ['telemetry_trace', 'telemetry_trace_test']
        for view_name in view_names:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        sql.SQL("SELECT COUNT(*) FROM gold.{}").format(
                            sql.Identifier(view_name)
                        )
                    )
                    row_count = cur.fetchone()[0]
                    print(f"  - Total rows in gold.{view_name}: {row_count:,}")
                    break
            except:
                continue
        else:
            print("  (Could not get row count - view may not exist yet)")
        
        conn.close()
        return True
        
    except psycopg.errors.DuplicateTable:
        print("View already exists. Use DROP MATERIALIZED VIEW first if you want to recreate.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error executing migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    script_path = sys.argv[1] if len(sys.argv) > 1 else 'init-db/14-create-telemetry-trace-view.sql'
    run_migration(script_path)

