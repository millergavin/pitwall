"""
Refresh the gold.driver_standings_progression and gold.constructor_standings_progression
materialized views after schema changes.
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def refresh_standings_views():
    """Drop and recreate the standings progression views with new columns."""
    
    # Database connection parameters
    conn_params = {
        'host': os.getenv('PGHOST', 'localhost'),
        'port': os.getenv('PGPORT', '5433'),
        'database': os.getenv('PGDATABASE', 'pitwall'),
        'user': os.getenv('PGUSER', 'pitwall_admin'),
        'password': os.getenv('PGPASSWORD', 'pitwall_admin')
    }
    
    print(f"Connecting to database at {conn_params['host']}:{conn_params['port']}...")
    
    try:
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                print("\n🔄 Dropping existing views...")
                
                # Drop the views
                cur.execute("DROP MATERIALIZED VIEW IF EXISTS gold.driver_standings_progression CASCADE;")
                print("  ✓ Dropped gold.driver_standings_progression")
                
                cur.execute("DROP MATERIALIZED VIEW IF EXISTS gold.constructor_standings_progression CASCADE;")
                print("  ✓ Dropped gold.constructor_standings_progression")
                
                conn.commit()
                
                print("\n🏗️  Recreating views with country fields...")
                
                # Recreate driver_standings_progression
                cur.execute("""
                    CREATE MATERIALIZED VIEW gold.driver_standings_progression AS
                    SELECT
                        m.season,
                        m.round_number,
                        s.session_id,
                        s.session_type,
                        m.meeting_official_name AS meeting_name,
                        m.meeting_name AS meeting_short_name,
                        co.country_code,
                        co.country_name,
                        co.emoji_flag,
                        co.flag_url,
                        r.driver_id,
                        dis.driver_number,
                        dis.driver_name,
                        dis.name_acronym,
                        d.headshot_url AS driver_headshot_url,
                        d.headshot_override AS driver_headshot_override,
                        dis.team_id,
                        dis.team_name,
                        dis.display_name,
                        dis.color_hex,
                        dis.logo_url AS team_logo_url,
                        r.finish_position,
                        r.fastest_lap,
                        r.points AS session_points,
                        SUM(r.points) OVER (
                            PARTITION BY m.season, r.driver_id
                            ORDER BY 
                                m.round_number,
                                CASE WHEN s.session_type = 'sprint' THEN 0 ELSE 1 END
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS cumulative_points
                    FROM silver.results r
                    INNER JOIN silver.sessions s ON r.session_id = s.session_id
                    INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
                    INNER JOIN silver.circuits c ON m.circuit_id = c.circuit_id
                    INNER JOIN silver.countries co ON c.country_code = co.country_code
                    INNER JOIN silver.driver_id_by_session dis 
                        ON s.session_id = dis.session_id 
                        AND r.driver_id = dis.driver_id
                    INNER JOIN silver.drivers d ON r.driver_id = d.driver_id
                    WHERE s.points_awarding IN ('race', 'sprint')
                      AND r.status = 'finished'
                    ORDER BY 
                        m.season,
                        r.driver_id,
                        m.round_number,
                        CASE WHEN s.session_type = 'sprint' THEN 0 ELSE 1 END
                """)
                print("  ✓ Created gold.driver_standings_progression")
                
                # Create indexes for driver_standings_progression
                cur.execute("""
                    CREATE INDEX idx_driver_standings_progression_season_driver 
                        ON gold.driver_standings_progression(season, driver_id)
                """)
                cur.execute("""
                    CREATE INDEX idx_driver_standings_progression_session 
                        ON gold.driver_standings_progression(session_id)
                """)
                print("  ✓ Created indexes for driver_standings_progression")
                
                # Recreate constructor_standings_progression
                cur.execute("""
                    CREATE MATERIALIZED VIEW gold.constructor_standings_progression AS
                    SELECT
                        m.season,
                        m.round_number,
                        s.session_id,
                        s.session_type,
                        m.meeting_official_name AS meeting_name,
                        m.meeting_name AS meeting_short_name,
                        co.country_code,
                        co.country_name,
                        co.emoji_flag,
                        co.flag_url,
                        dis.team_id,
                        dis.team_name,
                        dis.display_name,
                        dis.color_hex,
                        dis.logo_url AS team_logo_url,
                        SUM(r.points) AS session_points,
                        SUM(SUM(r.points)) OVER (
                            PARTITION BY m.season, dis.team_id
                            ORDER BY 
                                m.round_number,
                                CASE WHEN s.session_type = 'sprint' THEN 0 ELSE 1 END
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS cumulative_points
                    FROM silver.results r
                    INNER JOIN silver.sessions s ON r.session_id = s.session_id
                    INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
                    INNER JOIN silver.circuits c ON m.circuit_id = c.circuit_id
                    INNER JOIN silver.countries co ON c.country_code = co.country_code
                    INNER JOIN silver.driver_id_by_session dis 
                        ON s.session_id = dis.session_id 
                        AND r.driver_id = dis.driver_id
                    WHERE s.points_awarding IN ('race', 'sprint')
                    GROUP BY
                        m.season,
                        m.round_number,
                        s.session_id,
                        s.session_type,
                        m.meeting_official_name,
                        m.meeting_name,
                        co.country_code,
                        co.country_name,
                        co.emoji_flag,
                        co.flag_url,
                        dis.team_id,
                        dis.team_name,
                        dis.display_name,
                        dis.color_hex,
                        dis.logo_url
                    ORDER BY 
                        m.season,
                        dis.team_id,
                        m.round_number,
                        CASE WHEN s.session_type = 'sprint' THEN 0 ELSE 1 END
                """)
                print("  ✓ Created gold.constructor_standings_progression")
                
                # Create indexes for constructor_standings_progression
                cur.execute("""
                    CREATE INDEX idx_constructor_standings_progression_season_team 
                        ON gold.constructor_standings_progression(season, team_id)
                """)
                cur.execute("""
                    CREATE INDEX idx_constructor_standings_progression_session 
                        ON gold.constructor_standings_progression(session_id)
                """)
                print("  ✓ Created indexes for constructor_standings_progression")
                
                conn.commit()
                
                print("\n📊 Checking view data...")
                
                # Check driver standings progression
                cur.execute("""
                    SELECT 
                        season,
                        round_number,
                        meeting_short_name,
                        emoji_flag,
                        country_name,
                        driver_name,
                        cumulative_points
                    FROM gold.driver_standings_progression
                    WHERE season = 2024
                    ORDER BY season DESC, round_number DESC, cumulative_points DESC
                    LIMIT 5
                """)
                
                print("\n🏁 Sample driver standings (2024 season, latest round):")
                for row in cur.fetchall():
                    season, round_num, meeting, emoji, country, driver, points = row
                    print(f"  {emoji} {country:20s} - {driver:20s} {points:6.1f} pts")
                
                # Check constructor standings progression
                cur.execute("""
                    SELECT 
                        season,
                        round_number,
                        meeting_short_name,
                        emoji_flag,
                        country_name,
                        team_name,
                        cumulative_points
                    FROM gold.constructor_standings_progression
                    WHERE season = 2024
                    ORDER BY season DESC, round_number DESC, cumulative_points DESC
                    LIMIT 5
                """)
                
                print("\n🏆 Sample constructor standings (2024 season, latest round):")
                for row in cur.fetchall():
                    season, round_num, meeting, emoji, country, team, points = row
                    print(f"  {emoji} {country:20s} - {team:30s} {points:6.1f} pts")
                
                # Get row counts
                cur.execute("SELECT COUNT(*) FROM gold.driver_standings_progression")
                driver_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM gold.constructor_standings_progression")
                constructor_count = cur.fetchone()[0]
                
                print(f"\n✅ Views refreshed successfully!")
                print(f"   - driver_standings_progression: {driver_count:,} rows")
                print(f"   - constructor_standings_progression: {constructor_count:,} rows")
                
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    refresh_standings_views()
