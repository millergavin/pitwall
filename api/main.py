"""
FastAPI backend for Pitwall - serves gold layer data to frontend
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import subprocess
import threading
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import psycopg
from psycopg_pool import ConnectionPool  
from psycopg.rows import dict_row

load_dotenv()

# Track database update status
update_status = {
    "is_running": False,
    "started_at": None,
    "completed_at": None,
    "phase": None,
    "success": None,
    "error": None,
    "log_file": None
}

# Database connection pool
db_pool: ConnectionPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connection pool lifecycle"""
    global db_pool
    # Create connection pool
    db_pool = ConnectionPool(
        conninfo=(
            f"host={os.getenv('PGHOST', 'localhost')} "
            f"port={os.getenv('PGPORT', '5433')} "
            f"dbname={os.getenv('PGDATABASE', 'pitwall')} "
            f"user={os.getenv('PGUSER', 'pitwall')} "
            f"password={os.getenv('PGPASSWORD', 'pitwall')}"
        ),
        min_size=1,
        max_size=10,
    )
    yield
    # Cleanup
    if db_pool:
        db_pool.close()


app = FastAPI(
    title="Pitwall API",
    description="API for F1 data visualization",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow frontend origins
ALLOWED_ORIGINS = [
    "http://localhost:5174",
    "http://localhost:3000",
    "https://pitwall.one",
    "https://www.pitwall.one",
    os.getenv("FRONTEND_URL", ""),  # Optional additional URL
]
# Also allow any vercel.app subdomain for preview deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection():
    """Get a database connection from the pool"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    return db_pool.getconn()


@app.get("/")
def root():
    """Health check endpoint"""
    return {"message": "Pitwall API", "status": "healthy"}


@app.get("/api/drivers")
def get_drivers(season: int = None):
    """Get drivers from gold.dim_drivers"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if season:
                cur.execute(
                    "SELECT * FROM gold.dim_drivers WHERE season = %s ORDER BY full_name",
                    (season,)
                )
            else:
                cur.execute("SELECT * FROM gold.dim_drivers ORDER BY season DESC, full_name")
            return cur.fetchall()


@app.get("/api/teams")
def get_teams(season: int = None):
    """Get teams from gold.dim_teams"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if season:
                cur.execute(
                    "SELECT * FROM gold.dim_teams WHERE season = %s ORDER BY team_name",
                    (season,)
                )
            else:
                cur.execute("SELECT * FROM gold.dim_teams ORDER BY season DESC, team_name")
            return cur.fetchall()


@app.get("/api/meetings")
def get_meetings(season: int = None):
    """Get meetings from gold.dim_meetings"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if season:
                cur.execute(
                    "SELECT * FROM gold.dim_meetings WHERE season = %s ORDER BY round_number",
                    (season,)
                )
            else:
                cur.execute("SELECT * FROM gold.dim_meetings ORDER BY season DESC, round_number")
            return cur.fetchall()


@app.get("/api/circuits")
def get_circuits():
    """Get circuits from gold.dim_circuits"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM gold.dim_circuits ORDER BY circuit_name")
            return cur.fetchall()


@app.get("/api/images")
def get_images(
    circuit_id: str = None,
    driver_id: str = None,
    team_id: str = None,
    meeting_id: str = None,
    image_type: str = None,
    tag: str = None,
    year: int = None,
    cover_only: bool = False
):
    """
    Get images with flexible filtering by entity associations.
    
    Args:
        circuit_id: Filter by circuit (e.g., 'monaco')
        driver_id: Filter by driver (e.g., 'lewis-hamilton')
        team_id: Filter by team (e.g., 'mercedes')
        meeting_id: Filter by meeting/race weekend
        image_type: Filter by type ('action', 'portrait', 'podium', 'destination', 'historical')
        tag: Filter by tag
        year: Filter by year
        cover_only: If true, only return cover/hero images
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            query = """
                SELECT image_id, file_path, is_cover, image_type, caption, credit, 
                       year, display_order, created_at, circuit_id, driver_ids, 
                       team_ids, meeting_id, tags
                FROM silver.images
                WHERE 1=1
            """
            params = []
            
            if circuit_id:
                query += " AND circuit_id = %s"
                params.append(circuit_id)
            
            if driver_id:
                query += " AND %s = ANY(driver_ids)"
                params.append(driver_id)
            
            if team_id:
                query += " AND %s = ANY(team_ids)"
                params.append(team_id)
            
            if meeting_id:
                query += " AND meeting_id = %s"
                params.append(meeting_id)
            
            if image_type:
                query += " AND image_type = %s"
                params.append(image_type)
            
            if tag:
                query += " AND %s = ANY(tags)"
                params.append(tag)
            
            if year:
                query += " AND year = %s"
                params.append(year)
            
            if cover_only:
                query += " AND is_cover = TRUE"
            
            query += " ORDER BY is_cover DESC, display_order, created_at DESC"
            
            cur.execute(query, params)
            return cur.fetchall()


@app.get("/api/circuits/{circuit_id}/images")
def get_circuit_images(circuit_id: str, image_type: str = None, cover_only: bool = False):
    """Get images for a specific circuit (convenience endpoint)."""
    return get_images(circuit_id=circuit_id, image_type=image_type, cover_only=cover_only)


@app.get("/api/meetings/{meeting_id}")
def get_meeting(meeting_id: str):
    """Get a specific meeting by ID"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM gold.dim_meetings WHERE meeting_id = %s",
                (meeting_id,)
            )
            meeting = cur.fetchone()
            if not meeting:
                raise HTTPException(status_code=404, detail="Meeting not found")
            return meeting


@app.get("/api/meetings/{meeting_id}/sessions")
def get_meeting_sessions(meeting_id: str):
    """Get all sessions for a specific meeting"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Get sessions from session_summary, ordered by session type priority
            cur.execute("""
                SELECT 
                    season, round_number, meeting_official_name, meeting_id,
                    circuit_id, circuit_name, circuit_short_name,
                    session_id, session_type::text, scheduled_laps,
                    start_time, end_time, completed_laps,
                    winner_driver_id, winner_team_id, 
                    winner_driver_name, winner_team_name,
                    red_flag_count, yellow_flag_count, 
                    safety_car_count, virtual_safety_car_count,
                    classified_finishers, air_temperature, track_temperature,
                    rain_flag, weather_conditions, overtakes_count,
                    CASE session_type
                        WHEN 'p1' THEN 1
                        WHEN 'p2' THEN 2
                        WHEN 'p3' THEN 3
                        WHEN 'sprint_quali' THEN 4
                        WHEN 'sprint' THEN 5
                        WHEN 'quali' THEN 6
                        WHEN 'race' THEN 7
                        ELSE 99
                    END as sort_order
                FROM gold.session_summary
                WHERE meeting_id = %s
                ORDER BY sort_order, start_time
            """, (meeting_id,))
            return cur.fetchall()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    """Get session summary by ID"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT *, session_type::text as session_type FROM gold.session_summary WHERE session_id = %s",
                (session_id,)
            )
            session = cur.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return session


@app.get("/api/sessions/{session_id}/classification")
def get_session_classification(session_id: str):
    """Get classification (results) for a specific session"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT 
                    sc.season, sc.round_number, sc.meeting_official_name, sc.circuit_id,
                    sc.circuit_name, sc.circuit_short_name, sc.session_type::text as session_type,
                    sc.session_id, sc.driver_id, sc.driver_number, sc.driver_name, sc.name_acronym,
                    sc.team_id, sc.team_name, sc.display_name, sc.color_hex, sc.grid_position,
                    sc.finish_position, sc.status::text as status, sc.laps_completed, 
                    sc.duration_ms, sc.gap_to_leader_ms, sc.best_lap_ms, sc.fastest_lap, sc.points,
                    dt.logo_url
                FROM gold.session_classification sc
                LEFT JOIN gold.dim_teams dt ON sc.team_id = dt.team_id AND sc.season = dt.season
                WHERE sc.session_id = %s
                ORDER BY sc.finish_position NULLS LAST, sc.driver_name
            """, (session_id,))
            return cur.fetchall()


@app.get("/api/session-summary")
def get_session_summary(season: int = None, session_type: str = None):
    """Get session summaries from gold.session_summary"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            query = "SELECT *, session_type::text as session_type FROM gold.session_summary WHERE 1=1"
            params = []
            
            if season:
                query += " AND season = %s"
                params.append(season)
            
            if session_type:
                query += " AND session_type = %s"
                params.append(session_type)
            
            query += " ORDER BY season DESC, round_number, start_time"
            
            cur.execute(query, params)
            return cur.fetchall()


@app.get("/api/driver-standings")
def get_driver_standings(season: int = None):
    """Get driver standings progression from gold.driver_standings_progression"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if season:
                cur.execute(
                    "SELECT * FROM gold.driver_standings_progression WHERE season = %s ORDER BY round_number, cumulative_points DESC",
                    (season,)
                )
            else:
                cur.execute(
                    "SELECT * FROM gold.driver_standings_progression ORDER BY season DESC, round_number, cumulative_points DESC"
                )
            return cur.fetchall()


@app.get("/api/lap-times")
def get_lap_times(session_id: str = None, driver_id: str = None):
    """Get lap times from gold.lap_times"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            query = "SELECT * FROM gold.lap_times WHERE 1=1"
            params = []
            
            if session_id:
                query += " AND session_id = %s"
                params.append(session_id)
            
            if driver_id:
                query += " AND driver_id = %s"
                params.append(driver_id)
            
            query += " ORDER BY lap_number"
            
            cur.execute(query, params)
            return cur.fetchall()


@app.get("/api/circuit-overtake-stats")
def get_circuit_overtake_stats():
    """Get circuit overtake statistics"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM gold.circuit_overtake_stats ORDER BY overtakes_race_avg DESC NULLS LAST")
            return cur.fetchall()


@app.get("/api/standings/drivers")
def get_driver_standings_by_meeting(season: int = 2024):
    """
    Get driver championship standings progression by meeting.
    Returns the cumulative points for each driver after each meeting (round).
    Filters to only the top 20 drivers by number of meetings participated.
    Fills in missing rounds with carried-forward cumulative points.
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    query = """
        WITH driver_meeting_counts AS (
            SELECT 
                driver_id,
                COUNT(DISTINCT round_number) as meeting_count
            FROM gold.driver_standings_progression
            WHERE season = %s
            GROUP BY driver_id
            ORDER BY meeting_count DESC
            LIMIT 20
        ),
        all_rounds AS (
            SELECT DISTINCT 
                round_number,
                meeting_name,
                meeting_short_name,
                country_code,
                emoji_flag,
                flag_url
            FROM gold.driver_standings_progression
            WHERE season = %s
        ),
        top_drivers AS (
            SELECT DISTINCT ON (dsp.driver_id)
                dsp.driver_id,
                dsp.driver_number,
                dsp.driver_name,
                dsp.name_acronym,
                dsp.team_id,
                dsp.team_name,
                dsp.color_hex,
                dt.logo_url
            FROM gold.driver_standings_progression dsp
            INNER JOIN driver_meeting_counts dmc ON dsp.driver_id = dmc.driver_id
            LEFT JOIN gold.dim_teams dt ON dsp.team_id = dt.team_id AND dt.season = %s
            WHERE dsp.season = %s
            ORDER BY dsp.driver_id, dsp.round_number DESC
        ),
        driver_round_grid AS (
            SELECT 
                td.*,
                ar.round_number,
                ar.meeting_name,
                ar.meeting_short_name,
                ar.country_code,
                ar.emoji_flag,
                ar.flag_url
            FROM top_drivers td
            CROSS JOIN all_rounds ar
        ),
        actual_points AS (
            SELECT 
                dsp.driver_id,
                dsp.round_number,
                MAX(dsp.cumulative_points) as cumulative_points
            FROM gold.driver_standings_progression dsp
            INNER JOIN driver_meeting_counts dmc ON dsp.driver_id = dmc.driver_id
            WHERE dsp.season = %s
            GROUP BY dsp.driver_id, dsp.round_number
        )
        SELECT 
            %s as season,
            drg.round_number,
            drg.meeting_name,
            drg.meeting_short_name,
            drg.country_code,
            drg.emoji_flag,
            drg.flag_url,
            drg.driver_id,
            drg.driver_number,
            drg.driver_name,
            drg.name_acronym,
            drg.team_id,
            drg.team_name,
            drg.color_hex,
            drg.logo_url,
            COALESCE(
                ap.cumulative_points,
                (SELECT MAX(ap2.cumulative_points) 
                 FROM actual_points ap2 
                 WHERE ap2.driver_id = drg.driver_id 
                   AND ap2.round_number < drg.round_number),
                0
            ) as cumulative_points
        FROM driver_round_grid drg
        LEFT JOIN actual_points ap 
            ON drg.driver_id = ap.driver_id 
            AND drg.round_number = ap.round_number
        ORDER BY drg.round_number, drg.driver_name
    """
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (season, season, season, season, season, season))
            return cur.fetchall()


@app.get("/api/standings/constructors")
def get_constructor_standings_by_meeting(season: int = 2024):
    """
    Get constructor championship standings progression by meeting.
    Returns the cumulative points for each team after each meeting (round).
    Filters to only teams that participated in the season (top 10 by meeting count).
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    query = """
        WITH team_meeting_counts AS (
            SELECT 
                team_id,
                COUNT(DISTINCT round_number) as meeting_count
            FROM gold.constructor_standings_progression
            WHERE season = %s
            GROUP BY team_id
            ORDER BY meeting_count DESC
            LIMIT 10
        )
        SELECT 
            csp.season,
            csp.round_number,
            csp.meeting_name,
            csp.meeting_short_name,
            csp.country_code,
            csp.emoji_flag,
            csp.flag_url,
            csp.team_id,
            csp.team_name,
            csp.display_name,
            csp.color_hex,
            dt.logo_url,
            MAX(csp.cumulative_points) as cumulative_points
        FROM gold.constructor_standings_progression csp
        INNER JOIN team_meeting_counts tmc ON csp.team_id = tmc.team_id
        LEFT JOIN gold.dim_teams dt ON csp.team_id = dt.team_id AND dt.season = csp.season
        WHERE csp.season = %s
        GROUP BY 
            csp.season, csp.round_number, csp.meeting_name, csp.meeting_short_name,
            csp.country_code, csp.emoji_flag, csp.flag_url, csp.team_id, csp.team_name, csp.display_name, csp.color_hex, dt.logo_url
        ORDER BY csp.round_number, csp.team_name
    """
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (season, season))
            return cur.fetchall()


@app.get("/api/teams/roster")
def get_teams_roster(season: int = 2025):
    """
    Get the current roster of teams for a season.
    Returns one entry per team with their branding and car image.
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    query = """
        SELECT DISTINCT ON (team_id)
            team_id,
            team_name,
            display_name,
            color_hex,
            logo_url,
            car_image_url
        FROM silver.team_branding
        WHERE season = %s
        ORDER BY team_id, team_name
    """
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (season,))
            return cur.fetchall()


@app.get("/api/drivers/roster")
def get_drivers_roster(season: int = 2025):
    """
    Get the current roster of permanent drivers for a season.
    Returns one entry per driver with their most recent team information.
    Filters to only the 20 permanent drivers (those with the most sessions).
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    query = """
        WITH driver_session_counts AS (
            -- Count sessions per driver in the season
            SELECT 
                driver_id,
                COUNT(DISTINCT session_id) as session_count
            FROM gold.driver_standings_progression
            WHERE season = %s
            GROUP BY driver_id
            ORDER BY session_count DESC
            LIMIT 20
        ),
        latest_driver_info AS (
            -- Get the most recent appearance for each top driver
            SELECT DISTINCT ON (dsp.driver_id)
                dsp.driver_id,
                dsp.driver_number,
                d.first_name,
                d.last_name,
                d.full_name,
                dsp.name_acronym,
                d.headshot_url,
                d.headshot_override,
                dsp.team_id,
                dsp.team_name,
                dsp.color_hex,
                dsp.team_logo_url,
                dsp.round_number
            FROM gold.driver_standings_progression dsp
            INNER JOIN driver_session_counts dsc ON dsp.driver_id = dsc.driver_id
            INNER JOIN silver.drivers d ON dsp.driver_id = d.driver_id
            WHERE dsp.season = %s
            ORDER BY dsp.driver_id, dsp.round_number DESC
        )
        SELECT 
            driver_id,
            driver_number,
            first_name,
            last_name,
            full_name,
            name_acronym,
            headshot_url,
            headshot_override,
            team_id,
            team_name,
            color_hex,
            team_logo_url
        FROM latest_driver_info
        ORDER BY driver_number
    """
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (season, season))
            return cur.fetchall()


@app.get("/api/drivers/{driver_id:path}")
def get_driver_detail(driver_id: str, season: int = 2025):
    """
    Get detailed information for a specific driver including:
    - Driver bio info
    - Season stats (points, wins, podiums)
    - Recent race results
    - Season progression
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Get driver basic info with team
            cur.execute("""
                SELECT DISTINCT ON (d.driver_id)
                    d.driver_id,
                    d.first_name,
                    d.last_name,
                    d.full_name,
                    d.name_acronym,
                    d.country_code,
                    d.headshot_url,
                    d.headshot_override,
                    d.wikipedia_id,
                    d.birthdate,
                    dd.driver_number,
                    dd.primary_team_id,
                    dd.primary_team_name,
                    dt.color_hex,
                    dt.logo_url as team_logo_url,
                    dt.display_name as team_display_name
                FROM silver.drivers d
                LEFT JOIN gold.dim_drivers dd ON d.driver_id = dd.driver_id AND dd.season = %s
                LEFT JOIN gold.dim_teams dt ON dd.primary_team_id = dt.team_id AND dt.season = %s
                WHERE d.driver_id = %s
                ORDER BY d.driver_id, dd.season DESC
            """, (season, season, driver_id))
            
            driver_info = cur.fetchone()
            if not driver_info:
                raise HTTPException(status_code=404, detail="Driver not found")
            
            # Get season stats
            cur.execute("""
                SELECT 
                    MAX(cumulative_points) as total_points,
                    COUNT(CASE WHEN finish_position = 1 THEN 1 END) as wins,
                    COUNT(CASE WHEN finish_position <= 3 THEN 1 END) as podiums,
                    COUNT(CASE WHEN finish_position <= 10 THEN 1 END) as points_finishes,
                    COUNT(DISTINCT round_number) as races_entered,
                    COUNT(CASE WHEN fastest_lap THEN 1 END) as fastest_laps
                FROM gold.driver_standings_progression
                WHERE driver_id = %s AND season = %s
            """, (driver_id, season))
            
            season_stats = cur.fetchone()
            
            # Get championship position
            cur.execute("""
                WITH latest_standings AS (
                    SELECT 
                        driver_id,
                        MAX(cumulative_points) as total_points
                    FROM gold.driver_standings_progression
                    WHERE season = %s
                    GROUP BY driver_id
                )
                SELECT 
                    COUNT(*) + 1 as championship_position
                FROM latest_standings
                WHERE total_points > (
                    SELECT total_points 
                    FROM latest_standings 
                    WHERE driver_id = %s
                )
            """, (season, driver_id))
            
            position_result = cur.fetchone()
            championship_position = position_result['championship_position'] if position_result else None
            
            # Get recent results (last 5 races)
            cur.execute("""
                SELECT 
                    dsp.round_number,
                    dsp.meeting_short_name,
                    dsp.session_type::text,
                    dsp.finish_position,
                    dsp.session_points,
                    dsp.fastest_lap,
                    sc.grid_position,
                    sc.status::text,
                    dsp.country_code,
                    dsp.emoji_flag
                FROM gold.driver_standings_progression dsp
                LEFT JOIN gold.session_classification sc 
                    ON dsp.session_id = sc.session_id 
                    AND dsp.driver_id = sc.driver_id
                WHERE dsp.driver_id = %s AND dsp.season = %s
                ORDER BY dsp.round_number DESC
                LIMIT 5
            """, (driver_id, season))
            
            recent_results = cur.fetchall()
            
            # Get season progression (all rounds)
            cur.execute("""
                SELECT 
                    round_number,
                    meeting_short_name,
                    cumulative_points,
                    session_points,
                    finish_position,
                    emoji_flag
                FROM gold.driver_standings_progression
                WHERE driver_id = %s AND season = %s
                ORDER BY round_number
            """, (driver_id, season))
            
            progression = cur.fetchall()
            
            return {
                "driver": driver_info,
                "season_stats": season_stats,
                "championship_position": championship_position,
                "recent_results": recent_results,
                "season_progression": progression,
            }


@app.get("/api/teams/{team_id:path}")
def get_team_detail(team_id: str, season: int = 2025):
    """
    Get detailed information for a specific team including:
    - Team info and branding
    - Season stats (points, wins, podiums)
    - Current drivers
    - Recent race results
    - Season progression
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Get team basic info
            cur.execute("""
                SELECT 
                    t.team_id,
                    dt.team_name,
                    dt.display_name,
                    dt.color_hex,
                    dt.logo_url,
                    tb.car_image_url
                FROM silver.teams t
                LEFT JOIN gold.dim_teams dt ON t.team_id = dt.team_id AND dt.season = %s
                LEFT JOIN silver.team_branding tb ON t.team_id = tb.team_id AND tb.season = %s
                WHERE t.team_id = %s
                LIMIT 1
            """, (season, season, team_id))
            
            team_info = cur.fetchone()
            if not team_info:
                raise HTTPException(status_code=404, detail="Team not found")
            
            # Get season stats
            cur.execute("""
                SELECT 
                    MAX(cumulative_points) as total_points,
                    COUNT(DISTINCT CASE WHEN finish_position = 1 THEN round_number END) as wins,
                    COUNT(DISTINCT CASE WHEN finish_position <= 3 THEN round_number END) as podiums,
                    COUNT(DISTINCT CASE WHEN finish_position <= 10 THEN round_number END) as points_finishes,
                    COUNT(DISTINCT round_number) as races_entered,
                    COUNT(CASE WHEN fastest_lap THEN 1 END) as fastest_laps
                FROM gold.constructor_standings_progression
                WHERE team_id = %s AND season = %s
            """, (team_id, season))
            
            season_stats = cur.fetchone()
            
            # Get championship position
            cur.execute("""
                WITH latest_standings AS (
                    SELECT 
                        team_id,
                        MAX(cumulative_points) as total_points
                    FROM gold.constructor_standings_progression
                    WHERE season = %s
                    GROUP BY team_id
                )
                SELECT 
                    COUNT(*) + 1 as championship_position
                FROM latest_standings
                WHERE total_points > (
                    SELECT total_points 
                    FROM latest_standings 
                    WHERE team_id = %s
                )
            """, (season, team_id))
            
            position_result = cur.fetchone()
            championship_position = position_result['championship_position'] if position_result else None
            
            # Get current drivers for the team
            cur.execute("""
                SELECT DISTINCT ON (d.driver_id)
                    d.driver_id,
                    dd.driver_number,
                    d.full_name,
                    d.name_acronym,
                    d.headshot_url,
                    d.headshot_override,
                    MAX(dsp.cumulative_points) as driver_points
                FROM silver.drivers d
                INNER JOIN gold.dim_drivers dd ON d.driver_id = dd.driver_id AND dd.season = %s
                INNER JOIN gold.driver_standings_progression dsp ON d.driver_id = dsp.driver_id AND dsp.season = %s
                WHERE dd.primary_team_id = %s
                GROUP BY d.driver_id, dd.driver_number, d.full_name, d.name_acronym, d.headshot_url, d.headshot_override
                ORDER BY d.driver_id, driver_points DESC
            """, (season, season, team_id))
            
            drivers = cur.fetchall()
            
            # Get recent results (last 5 rounds with both drivers)
            cur.execute("""
                SELECT DISTINCT ON (csp.round_number, csp.session_type)
                    csp.round_number,
                    csp.meeting_short_name,
                    csp.session_type::text,
                    csp.session_points,
                    csp.country_code,
                    csp.emoji_flag
                FROM gold.constructor_standings_progression csp
                WHERE csp.team_id = %s AND csp.season = %s
                ORDER BY csp.round_number DESC, csp.session_type
                LIMIT 5
            """, (team_id, season))
            
            recent_results = cur.fetchall()
            
            # Get season progression (all rounds)
            cur.execute("""
                SELECT DISTINCT ON (round_number)
                    round_number,
                    meeting_short_name,
                    MAX(cumulative_points) as cumulative_points,
                    MAX(session_points) as session_points,
                    emoji_flag
                FROM gold.constructor_standings_progression
                WHERE team_id = %s AND season = %s
                GROUP BY round_number, meeting_short_name, emoji_flag
                ORDER BY round_number
            """, (team_id, season))
            
            progression = cur.fetchall()
            
            return {
                "team": team_info,
                "season_stats": season_stats,
                "championship_position": championship_position,
                "drivers": drivers,
                "recent_results": recent_results,
                "season_progression": progression,
            }


# =============================================================================
# DATABASE UPDATE ENDPOINTS
# =============================================================================

def run_database_update_task(skip_high_volume: bool = True):
    """Background task to run database update."""
    global update_status
    
    try:
        update_status["phase"] = "starting"
        
        # Build command
        cmd = ["python3", "update_database.py"]
        if skip_high_volume:
            cmd.append("--skip-high-volume")
        cmd.append("--json")
        
        update_status["phase"] = "running"
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Project root
        )
        
        update_status["completed_at"] = datetime.now().isoformat()
        
        if result.returncode == 0:
            update_status["success"] = True
            update_status["phase"] = "completed"
            # Try to parse output for log file
            try:
                import json
                output = json.loads(result.stdout)
                update_status["log_file"] = output.get("log_file")
            except:
                pass
        else:
            update_status["success"] = False
            update_status["phase"] = "failed"
            update_status["error"] = result.stderr[-1000:] if result.stderr else result.stdout[-1000:]
            
    except subprocess.TimeoutExpired:
        update_status["success"] = False
        update_status["phase"] = "timeout"
        update_status["error"] = "Update timed out after 1 hour"
        update_status["completed_at"] = datetime.now().isoformat()
    except Exception as e:
        update_status["success"] = False
        update_status["phase"] = "error"
        update_status["error"] = str(e)
        update_status["completed_at"] = datetime.now().isoformat()
    finally:
        update_status["is_running"] = False


@app.get("/api/database/status")
def get_database_status():
    """
    Get current database statistics and update status.
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    with db_pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Get counts
            stats = {}
            
            cur.execute("SELECT COUNT(*) as count FROM silver.meetings")
            stats["meetings"] = cur.fetchone()["count"]
            
            cur.execute("SELECT COUNT(*) as count FROM silver.sessions")
            stats["sessions"] = cur.fetchone()["count"]
            
            cur.execute("SELECT COUNT(*) as count FROM silver.laps")
            stats["laps"] = cur.fetchone()["count"]
            
            cur.execute("SELECT COUNT(*) as count FROM silver.drivers")
            stats["drivers"] = cur.fetchone()["count"]
            
            # Get latest data info
            cur.execute("""
                SELECT MAX(season) as latest_season, 
                       MAX(date_start) as latest_meeting_date
                FROM silver.meetings
            """)
            latest = cur.fetchone()
            stats["latest_season"] = latest["latest_season"]
            stats["latest_meeting_date"] = str(latest["latest_meeting_date"]) if latest["latest_meeting_date"] else None
            
            # Get latest session
            cur.execute("""
                SELECT session_name, start_time, meeting_id
                FROM silver.sessions
                ORDER BY start_time DESC
                LIMIT 1
            """)
            latest_session = cur.fetchone()
            if latest_session:
                stats["latest_session"] = {
                    "name": latest_session["session_name"],
                    "start_time": str(latest_session["start_time"]),
                    "meeting_id": latest_session["meeting_id"]
                }
    
    return {
        "database": stats,
        "update": update_status
    }


@app.post("/api/database/update")
def trigger_database_update(
    background_tasks: BackgroundTasks,
    skip_high_volume: bool = True
):
    """
    Trigger a database update.
    
    Args:
        skip_high_volume: Skip GPS/telemetry data for faster updates (default: True)
    
    Returns:
        Status of the update request
    """
    global update_status
    
    if update_status["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Database update already in progress"
        )
    
    # Reset status
    update_status = {
        "is_running": True,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "phase": "queued",
        "success": None,
        "error": None,
        "log_file": None
    }
    
    # Start background task
    thread = threading.Thread(
        target=run_database_update_task,
        args=(skip_high_volume,)
    )
    thread.start()
    
    return {
        "message": "Database update started",
        "status": update_status
    }


@app.post("/api/database/refresh-gold")
def refresh_gold_views_endpoint():
    """
    Refresh only the gold materialized views (fast operation).
    """
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    
    views = [
        'gold.dim_drivers',
        'gold.dim_teams',
        'gold.dim_circuits',
        'gold.dim_meetings',
        'gold.driver_session_results',
        'gold.session_classification',
        'gold.session_summary',
        'gold.lap_times',
        'gold.lap_intervals',
        'gold.driver_standings_progression',
        'gold.constructor_standings_progression',
        'gold.circuit_overtake_stats',
    ]
    
    results = {"success": [], "failed": []}
    
    # Use individual connections for each view to prevent transaction abort cascade
    for view in views:
        try:
            with db_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
                    conn.commit()
            results["success"].append(view.split('.')[-1])
        except Exception as e:
            results["failed"].append({"view": view.split('.')[-1], "error": str(e)})
    
    return {
        "message": f"Refreshed {len(results['success'])} views",
        "results": results
    }

