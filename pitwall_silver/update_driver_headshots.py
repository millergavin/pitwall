"""
Update silver.drivers with high-quality headshot override URLs.
Maps first name to the AVIF image files in /assets/driver_headshots/
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_driver_headshots():
    """Update driver headshot_override with high-quality AVIF images."""
    
    # Database connection parameters
    conn_params = {
        'host': os.getenv('PGHOST', 'localhost'),
        'port': os.getenv('PGPORT', '5433'),
        'database': os.getenv('PGDATABASE', 'pitwall'),
        'user': os.getenv('PGUSER', 'pitwall_admin'),
        'password': os.getenv('PGPASSWORD', 'pitwall_admin')
    }
    
    # Map first names to driver_ids (handling cases where multiple drivers have same first name)
    # We want the active F1 drivers
    driver_headshot_mapping = {
        'drv:alexander-albon': 'alexander.avif',      # Alexander Albon (not Dunne)
        'drv:carlos-sainz': 'carlos.avif',
        'drv:charles-leclerc': 'charles.avif',
        'drv:esteban-ocon': 'esteban.avif',
        'drv:fernando-alonso': 'fernando.avif',
        'drv:franco-colapinto': 'franco.avif',
        'drv:gabriel-bortoleto': 'gabriel.avif',
        'drv:george-russell': 'george.avif',
        'drv:isack-hadjar': 'isack.avif',
        'drv:kimi-antonelli': 'kimi.avif',
        'drv:lance-stroll': 'lance.avif',
        'drv:lando-norris': 'lando.avif',
        'drv:lewis-hamilton': 'lewis.avif',
        'drv:liam-lawson': 'liam.avif',
        'drv:max-verstappen': 'max.avif',
        'drv:nico-hulkenberg': 'nico.avif',
        'drv:oliver-bearman': 'oliver.avif',
        'drv:oscar-piastri': 'oscar.avif',
        'drv:pierre-gasly': 'pierre.avif',
        'drv:yuki-tsunoda': 'yuki.avif',
    }
    
    print(f"Connecting to database at {conn_params['host']}:{conn_params['port']}...")
    
    try:
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Get current state
                cur.execute("""
                    SELECT driver_id, first_name, last_name, full_name, headshot_override
                    FROM silver.drivers
                    WHERE driver_id = ANY(%s)
                    ORDER BY first_name, last_name
                """, (list(driver_headshot_mapping.keys()),))
                
                drivers = cur.fetchall()
                print(f"\n📊 Found {len(drivers)} drivers to update")
                
                # Track updates
                updates = []
                
                for driver_id, first_name, last_name, full_name, current_override in drivers:
                    if driver_id in driver_headshot_mapping:
                        filename = driver_headshot_mapping[driver_id]
                        new_url = f'/assets/driver_headshots/{filename}'
                        
                        if current_override != new_url:
                            updates.append((new_url, driver_id))
                            status = '🆕' if not current_override else '🔄'
                            print(f"  {status} {full_name:25s} → {filename}")
                        else:
                            print(f"  ✓ {full_name:25s} (already set)")
                
                # Update the database
                if updates:
                    print(f"\n🚀 Updating {len(updates)} driver headshots...")
                    
                    for new_url, driver_id in updates:
                        cur.execute("""
                            UPDATE silver.drivers
                            SET headshot_override = %s
                            WHERE driver_id = %s
                        """, (new_url, driver_id))
                    
                    conn.commit()
                    print(f"✅ Successfully updated {len(updates)} driver headshots!")
                else:
                    print("\nℹ️  No updates needed - all headshots are already set!")
                
                # Show final state
                print("\n📋 Final headshot state:")
                cur.execute("""
                    SELECT driver_id, first_name, last_name, headshot_override
                    FROM silver.drivers
                    WHERE driver_id = ANY(%s)
                    ORDER BY first_name, last_name
                """, (list(driver_headshot_mapping.keys()),))
                
                for driver_id, first_name, last_name, override_url in cur.fetchall():
                    status = '✅' if override_url else '❌'
                    print(f"  {status} {first_name} {last_name:15s} → {override_url or 'None'}")
                
                # Count totals
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(headshot_override) as with_override,
                        COUNT(*) - COUNT(headshot_override) as without_override
                    FROM silver.drivers
                    WHERE driver_id = ANY(%s)
                """, (list(driver_headshot_mapping.keys()),))
                
                total, with_override, without_override = cur.fetchone()
                print(f"\n📊 Summary:")
                print(f"   Updated drivers: {total}")
                print(f"   With high-quality headshots: {with_override}")
                print(f"   Without overrides: {without_override}")
                
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    update_driver_headshots()
