"""
Add flag emojis and flag URLs to all countries in the silver.countries table.
Flag emojis are generated from ISO 3166-1 alpha-2 country codes.
Flag URLs use flagcdn.com with the alpha-2 country code.
"""
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def country_code_to_emoji(alpha2_code):
    """
    Convert an ISO 3166-1 alpha-2 country code to a flag emoji.
    
    Flag emojis are represented by two Regional Indicator Symbol Letters.
    Each letter is mapped to a Unicode character in the range U+1F1E6 to U+1F1FF.
    
    Args:
        alpha2_code: Two-letter country code (e.g., 'US', 'GB', 'FR')
    
    Returns:
        Flag emoji string (e.g., '🇺🇸', '🇬🇧', '🇫🇷')
    """
    if not alpha2_code or len(alpha2_code) != 2:
        return None
    
    # Convert to uppercase
    alpha2_code = alpha2_code.upper()
    
    # Regional Indicator Symbol Letter A starts at U+1F1E6
    # Offset for 'A' is 0x1F1E6 - ord('A') = 0x1F1A5
    OFFSET = 0x1F1A5
    
    # Convert each letter to its regional indicator symbol
    flag_emoji = ''.join(chr(ord(char) + OFFSET) for char in alpha2_code)
    
    return flag_emoji


def country_code_to_flag_url(alpha2_code):
    """
    Convert an ISO 3166-1 alpha-2 country code to an Iconify circle-flags URL.
    
    Args:
        alpha2_code: Two-letter country code (e.g., 'US', 'GB', 'FR')
    
    Returns:
        Flag URL string (e.g., 'https://api.iconify.design/circle-flags/us.svg')
    """
    if not alpha2_code or len(alpha2_code) != 2:
        return None
    
    # Convert to lowercase for the URL
    alpha2_code = alpha2_code.lower()
    
    return f"https://api.iconify.design/circle-flags/{alpha2_code}.svg"


def add_country_flags():
    """Update all countries in silver.countries with their flag emojis and flag URLs."""
    
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
        # Connect to the database
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Get all countries with their alpha2 codes
                cur.execute("""
                    SELECT country_code, country_name, alpha2, emoji_flag, flag_url
                    FROM silver.countries
                    ORDER BY country_name
                """)
                
                countries = cur.fetchall()
                print(f"\nFound {len(countries)} countries in the database")
                
                # Prepare updates
                updates = []
                no_alpha2_codes = []
                
                for country_code, country_name, alpha2, existing_emoji, existing_flag_url in countries:
                    if not alpha2:
                        no_alpha2_codes.append((country_code, country_name))
                        continue
                    
                    # Generate flag emoji and URL (always update URL to ensure iconify format)
                    flag_emoji = country_code_to_emoji(alpha2) if not existing_emoji else existing_emoji
                    flag_url = country_code_to_flag_url(alpha2)
                    if flag_emoji and flag_url:
                        updates.append((flag_emoji, flag_url, country_code))
                
                print(f"\nSummary:")
                print(f"  - Countries without alpha2 codes: {len(no_alpha2_codes)}")
                print(f"  - Countries to update: {len(updates)}")
                
                if no_alpha2_codes:
                    print(f"\n⚠️  Countries without alpha2 codes (cannot generate flags):")
                    for code, name in no_alpha2_codes:
                        print(f"     {code}: {name}")
                
                # Update countries with flag emojis and URLs
                if updates:
                    print(f"\n🚀 Updating {len(updates)} countries with flag emojis and URLs...")
                    
                    execute_values(cur, """
                        UPDATE silver.countries
                        SET emoji_flag = data.emoji_flag,
                            flag_url = data.flag_url
                        FROM (VALUES %s) AS data(emoji_flag, flag_url, country_code)
                        WHERE silver.countries.country_code = data.country_code
                    """, updates)
                    
                    conn.commit()
                    print(f"✅ Successfully updated {len(updates)} countries!")
                    
                    # Show some examples
                    print(f"\n📍 Sample updates:")
                    cur.execute("""
                        SELECT country_code, country_name, emoji_flag, flag_url
                        FROM silver.countries
                        WHERE emoji_flag IS NOT NULL AND flag_url IS NOT NULL
                        ORDER BY country_name
                        LIMIT 10
                    """)
                    
                    for code, name, emoji, url in cur.fetchall():
                        print(f"     {emoji} {name} ({code}) - {url}")
                    
                    print(f"     ... and {len(updates) - 10} more" if len(updates) > 10 else "")
                else:
                    print("ℹ️  No updates needed - all countries already have flag emojis and URLs!")
                
                # Final count
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(emoji_flag) as with_emoji,
                        COUNT(flag_url) as with_url,
                        COUNT(*) FILTER (WHERE emoji_flag IS NULL OR flag_url IS NULL) as incomplete
                    FROM silver.countries
                """)
                
                total, with_emoji, with_url, incomplete = cur.fetchone()
                print(f"\n📊 Final statistics:")
                print(f"     Total countries: {total}")
                print(f"     With emoji flags: {with_emoji}")
                print(f"     With flag URLs: {with_url}")
                print(f"     Incomplete: {incomplete}")
                
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    add_country_flags()
