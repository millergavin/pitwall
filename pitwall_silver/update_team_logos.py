"""
Update silver.team_branding with logo URLs for team icon files.
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_team_logos():
    """Update team_branding with logo URLs based on team names."""
    
    # Database connection parameters
    conn_params = {
        'host': os.getenv('PGHOST', 'localhost'),
        'port': os.getenv('PGPORT', '5433'),
        'database': os.getenv('PGDATABASE', 'pitwall'),
        'user': os.getenv('PGUSER', 'pitwall_admin'),
        'password': os.getenv('PGPASSWORD', 'pitwall_admin')
    }
    
    # Map team names to logo file names
    # The key is the team_name pattern to match, value is the logo file path
    team_logo_mapping = {
        'Alpine': '/assets/team_logos/icons/alpine-icon.svg',
        'Aston Martin': '/assets/team_logos/icons/aston-martin-icon.svg',
        'Ferrari': '/assets/team_logos/icons/ferrari-icon.svg',
        'Haas F1 Team': '/assets/team_logos/icons/haas_icon.svg',
        'Kick Sauber': '/assets/team_logos/icons/kick_sauber-icon.svg',
        'Alfa Romeo': '/assets/team_logos/icons/kick_sauber-icon.svg',  # Same logo as Kick Sauber
        'McLaren': '/assets/team_logos/icons/mclaren_icon.svg',
        'Mercedes': '/assets/team_logos/icons/mercedes_icon.svg',
        'RB': '/assets/team_logos/icons/rb-icon.svg',
        'AlphaTauri': '/assets/team_logos/icons/rb-icon.svg',  # RB rebrand
        'Racing Bulls': '/assets/team_logos/icons/rb-icon.svg',  # RB rebrand
        'Red Bull Racing': '/assets/team_logos/icons/red_bull-icon.svg',
        'Williams': '/assets/team_logos/icons/williams-icon.svg',
    }
    
    print(f"Connecting to database at {conn_params['host']}:{conn_params['port']}...")
    
    try:
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Get current state of team_branding
                cur.execute("""
                    SELECT DISTINCT team_name, team_id, logo_url
                    FROM silver.team_branding
                    ORDER BY team_name
                """)
                
                teams = cur.fetchall()
                print(f"\n📊 Found {len(teams)} distinct team names in database")
                
                # Track updates
                updates = []
                not_found = []
                
                for team_name, team_id, current_logo_url in teams:
                    if team_name in team_logo_mapping:
                        logo_url = team_logo_mapping[team_name]
                        if current_logo_url != logo_url:
                            updates.append((logo_url, team_name))
                            print(f"  ✓ Will update: {team_name} → {logo_url}")
                        else:
                            print(f"  ℹ️  Already set: {team_name}")
                    else:
                        not_found.append(team_name)
                        print(f"  ⚠️  No logo mapping for: {team_name}")
                
                if not_found:
                    print(f"\n⚠️  Teams without logo mappings: {', '.join(not_found)}")
                
                # Update the database
                if updates:
                    print(f"\n🚀 Updating {len(updates)} team logo URLs...")
                    
                    update_count = 0
                    for logo_url, team_name in updates:
                        cur.execute("""
                            UPDATE silver.team_branding
                            SET logo_url = %s
                            WHERE team_name = %s
                        """, (logo_url, team_name))
                        update_count += cur.rowcount
                    
                    conn.commit()
                    print(f"✅ Successfully updated {update_count} rows!")
                else:
                    print("\nℹ️  No updates needed - all team logos are already set!")
                
                # Show final state
                print("\n📋 Final team branding state:")
                cur.execute("""
                    SELECT DISTINCT team_name, logo_url
                    FROM silver.team_branding
                    WHERE logo_url IS NOT NULL
                    ORDER BY team_name
                """)
                
                teams_with_logos = cur.fetchall()
                print(f"\n✨ Teams with logos: {len(teams_with_logos)}")
                for team_name, logo_url in teams_with_logos:
                    print(f"  • {team_name:20s} → {logo_url}")
                
                # Count teams without logos
                cur.execute("""
                    SELECT COUNT(DISTINCT team_name)
                    FROM silver.team_branding
                    WHERE logo_url IS NULL
                """)
                without_logos = cur.fetchone()[0]
                
                print(f"\n📊 Summary:")
                print(f"   Teams with logos: {len(teams_with_logos)}")
                print(f"   Teams without logos: {without_logos}")
                print(f"   Total distinct teams: {len(teams)}")
                
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    update_team_logos()
