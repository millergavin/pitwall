"""
Update silver.team_branding with car image URLs for 2025 season.
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_team_car_images():
    """Update team_branding with car image URLs."""
    
    # Database connection parameters
    conn_params = {
        'host': os.getenv('PGHOST', 'localhost'),
        'port': os.getenv('PGPORT', '5433'),
        'database': os.getenv('PGDATABASE', 'pitwall'),
        'user': os.getenv('PGUSER', 'pitwall_admin'),
        'password': os.getenv('PGPASSWORD', 'pitwall_admin')
    }
    
    # Map team_ids to car image filenames for 2025
    car_image_mapping = {
        'team:alpine': '/assets/car_images/2025/2025-alpine.avif',
        'team:aston-martin': '/assets/car_images/2025/2025-aston_martin.avif',
        'team:sauber-audi': '/assets/car_images/2025/2025-sauber.avif',
        'team:ferrari': '/assets/car_images/2025/2025-ferrari.avif',
        'team:haas': '/assets/car_images/2025/2025-haas.avif',
        'team:mclaren': '/assets/car_images/2025/2025-mclaren.avif',
        'team:mercedes': '/assets/car_images/2025/2025-mercedes.avif',
        'team:rb': '/assets/car_images/2025/2025-rb.avif',
        'team:red-bull': '/assets/car_images/2025/2025-red_bull.avif',
        'team:williams': '/assets/car_images/2025/2025-williams.avif',
    }
    
    print(f"Connecting to database at {conn_params['host']}:{conn_params['port']}...")
    
    try:
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Get current state for 2025
                cur.execute("""
                    SELECT DISTINCT team_id, team_name, car_image_url
                    FROM silver.team_branding
                    WHERE season = 2025
                    ORDER BY team_name
                """)
                
                teams = cur.fetchall()
                print(f"\n📊 Found {len(teams)} teams in 2025 season")
                
                # Track updates
                updates = []
                no_image = []
                
                for team_id, team_name, current_car_url in teams:
                    if team_id in car_image_mapping:
                        car_url = car_image_mapping[team_id]
                        if current_car_url != car_url:
                            updates.append((car_url, team_id))
                            status = '🆕' if not current_car_url else '🔄'
                            print(f"  {status} {team_name:20s} → {car_url.split('/')[-1]}")
                        else:
                            print(f"  ✓ {team_name:20s} (already set)")
                    else:
                        no_image.append((team_id, team_name))
                        print(f"  ⚠️  {team_name:20s} (no car image available)")
                
                # Update the database
                if updates:
                    print(f"\n🚀 Updating {len(updates)} team car images...")
                    
                    for car_url, team_id in updates:
                        # Update all rows for this team in 2025 season
                        cur.execute("""
                            UPDATE silver.team_branding
                            SET car_image_url = %s
                            WHERE team_id = %s AND season = 2025
                        """, (car_url, team_id))
                    
                    conn.commit()
                    print(f"✅ Successfully updated {len(updates)} team car images!")
                else:
                    print("\nℹ️  No updates needed - all car images are already set!")
                
                # Show final state
                print("\n📋 Final car image state (2025 season):")
                cur.execute("""
                    SELECT DISTINCT team_id, team_name, car_image_url
                    FROM silver.team_branding
                    WHERE season = 2025
                    ORDER BY team_name
                """)
                
                for team_id, team_name, car_url in cur.fetchall():
                    status = '✅' if car_url else '❌'
                    url_display = car_url.split('/')[-1] if car_url else 'None'
                    print(f"  {status} {team_name:20s} → {url_display}")
                
                # Count totals
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT team_id) as total_teams,
                        COUNT(DISTINCT CASE WHEN car_image_url IS NOT NULL THEN team_id END) as with_images
                    FROM silver.team_branding
                    WHERE season = 2025
                """)
                
                total, with_images = cur.fetchone()
                print(f"\n📊 Summary:")
                print(f"   Total teams (2025): {total}")
                print(f"   With car images: {with_images}")
                print(f"   Without car images: {total - with_images}")
                
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    update_team_car_images()
