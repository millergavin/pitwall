-- Gold layer materialized views
-- These views provide aggregated and enriched data for analytics and visualization

-- 1. Driver Standings Progression
-- Provides a season-long points timeline per driver, used to plot how the championship standings evolve after each sprint/race.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.driver_standings_progression AS
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
    CASE WHEN s.session_type = 'sprint' THEN 0 ELSE 1 END;

-- Create index on driver_standings_progression for performance
CREATE INDEX IF NOT EXISTS idx_driver_standings_progression_season_driver 
    ON gold.driver_standings_progression(season, driver_id);
CREATE INDEX IF NOT EXISTS idx_driver_standings_progression_session 
    ON gold.driver_standings_progression(session_id);

-- 2. Constructor Standings Progression
-- Provides a season-long points timeline per team, used to track and visualize the constructors' championship progression.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.constructor_standings_progression AS
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
    CASE WHEN s.session_type = 'sprint' THEN 0 ELSE 1 END;

-- Create index on constructor_standings_progression for performance
CREATE INDEX IF NOT EXISTS idx_constructor_standings_progression_season_team 
    ON gold.constructor_standings_progression(season, team_id);
CREATE INDEX IF NOT EXISTS idx_constructor_standings_progression_session 
    ON gold.constructor_standings_progression(session_id);

-- 3. Driver Session Results
-- Acts as the main fact table for per-session driver performance charts and tables across all session types.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.driver_session_results AS
SELECT
    m.season,
    m.round_number,
    m.meeting_official_name,
    c.circuit_name,
    c.timezone_tzid,
    s.session_id,
    s.session_type,
    s.start_time,
    s.end_time,
    r.driver_id,
    dis.driver_number,
    dis.driver_name,
    dis.name_acronym,
    dis.team_id,
    dis.team_name,
    dis.display_name,
    dis.color_hex,
    r.grid_position,
    r.finish_position,
    r.status,
    r.laps_completed,
    r.duration_ms,
    r.gap_to_leader_ms,
    r.points,
    r.fastest_lap,
    r.best_lap_ms,
    r.quali_lap_ms
FROM silver.results r
INNER JOIN silver.sessions s ON r.session_id = s.session_id
INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
INNER JOIN silver.circuits c ON m.circuit_id = c.circuit_id
INNER JOIN silver.driver_id_by_session dis 
    ON s.session_id = dis.session_id 
    AND r.driver_id = dis.driver_id
ORDER BY 
    m.season,
    s.session_id,
    r.finish_position NULLS LAST;

-- Create indexes on driver_session_results for performance
CREATE INDEX IF NOT EXISTS idx_driver_session_results_session_driver 
    ON gold.driver_session_results(session_id, driver_id);
CREATE INDEX IF NOT EXISTS idx_driver_session_results_season 
    ON gold.driver_session_results(season);
CREATE INDEX IF NOT EXISTS idx_driver_session_results_session_type 
    ON gold.driver_session_results(session_type);

-- 4. Session Classification
-- Provides a classification-oriented slice of results for race/sprint/quali sessions, optimized for timing sheet-style views.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.session_classification AS
SELECT
    m.season,
    m.round_number,
    m.meeting_official_name,
    c.circuit_id,
    c.circuit_name,
    c.circuit_short_name,
    s.session_type,
    s.session_id,
    r.driver_id,
    dis.driver_number,
    dis.driver_name,
    dis.name_acronym,
    dis.team_id,
    dis.team_name,
    dis.display_name,
    dis.color_hex,
    r.grid_position,
    r.finish_position,
    r.status,
    r.laps_completed,
    r.duration_ms,
    r.gap_to_leader_ms,
    r.best_lap_ms,
    r.fastest_lap,
    r.points
FROM silver.results r
INNER JOIN silver.sessions s ON r.session_id = s.session_id
INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
INNER JOIN silver.circuits c ON m.circuit_id = c.circuit_id
INNER JOIN silver.driver_id_by_session dis 
    ON s.session_id = dis.session_id 
    AND r.driver_id = dis.driver_id
WHERE s.session_type IN ('race', 'sprint', 'quali', 'sprint_quali')
  AND r.status != 'dns'
ORDER BY 
    m.season,
    s.session_id,
    r.finish_position NULLS LAST;

-- Create indexes on session_classification for performance
CREATE INDEX IF NOT EXISTS idx_session_classification_session_driver 
    ON gold.session_classification(session_id, driver_id);
CREATE INDEX IF NOT EXISTS idx_session_classification_season 
    ON gold.session_classification(season);
CREATE INDEX IF NOT EXISTS idx_session_classification_session_type 
    ON gold.session_classification(session_type);

-- 5. Session Summary
-- Rolls each session up to a single row with metadata, flags, winner info, completed laps, and weather aggregates.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.session_summary AS
SELECT
    m.season,
    m.round_number,
    m.meeting_official_name,
    m.meeting_id,
    c.circuit_id,
    c.circuit_name,
    c.circuit_short_name,
    s.session_id,
    s.session_type,
    s.scheduled_laps,
    s.start_time,
    s.end_time,
    -- Completed laps (max from results)
    MAX(r.laps_completed) AS completed_laps,
    -- Winner driver and team
    (SELECT r2.driver_id 
     FROM silver.results r2 
     WHERE r2.session_id = s.session_id 
       AND r2.finish_position = 1 
       AND r2.status = 'finished' 
     LIMIT 1) AS winner_driver_id,
    (SELECT dis2.team_id 
     FROM silver.results r2
     INNER JOIN silver.driver_id_by_session dis2 
         ON r2.session_id = dis2.session_id 
         AND r2.driver_id = dis2.driver_id
     WHERE r2.session_id = s.session_id 
       AND r2.finish_position = 1 
       AND r2.status = 'finished' 
     LIMIT 1) AS winner_team_id,
    (SELECT dis2.driver_name 
     FROM silver.results r2
     INNER JOIN silver.driver_id_by_session dis2 
         ON r2.session_id = dis2.session_id 
         AND r2.driver_id = dis2.driver_id
     WHERE r2.session_id = s.session_id 
       AND r2.finish_position = 1 
       AND r2.status = 'finished' 
     LIMIT 1) AS winner_driver_name,
    (SELECT dis2.team_name 
     FROM silver.results r2
     INNER JOIN silver.driver_id_by_session dis2 
         ON r2.session_id = dis2.session_id 
         AND r2.driver_id = dis2.driver_id
     WHERE r2.session_id = s.session_id 
       AND r2.finish_position = 1 
       AND r2.status = 'finished' 
     LIMIT 1) AS winner_team_name,
    -- Race control flags
    -- Red flag: count distinct occurrences
    COUNT(DISTINCT CASE WHEN rc.flag = 'RED' THEN rc.date END) AS red_flag_count,
    -- Yellow flag: count distinct occurrences
    COUNT(DISTINCT CASE WHEN rc.flag = 'YELLOW' THEN rc.date END) AS yellow_flag_count,
    -- Safety car: count distinct occurrences
    COUNT(DISTINCT CASE WHEN rc.message ILIKE '%safety car deployed%' THEN rc.date END) AS safety_car_count,
    -- VSC: count distinct occurrences
    COUNT(DISTINCT CASE WHEN rc.message ILIKE '%virtual safety car deployed%' OR rc.message ILIKE '%vsc deployed%' THEN rc.date END) AS virtual_safety_car_count,
    -- Classified finishers count
    COUNT(CASE WHEN r.status = 'finished' THEN 1 END) AS classified_finishers,
    -- Weather aggregates
    AVG(w.air_temp_c) AS air_temperature,
    AVG(w.track_temp_c) AS track_temperature,
    BOOL_OR(w.rainfall > 0) AS rain_flag,
    -- Simple weather conditions based on rainfall
    CASE 
        WHEN BOOL_OR(w.rainfall > 0) THEN 'Wet'
        ELSE 'Dry'
    END AS weather_conditions,
    -- Overtakes count (only for race and sprint)
    CASE 
        WHEN s.session_type IN ('race', 'sprint') 
        THEN (SELECT COUNT(*) FROM silver.overtakes o WHERE o.session_id = s.session_id)
        ELSE NULL
    END AS overtakes_count
FROM silver.sessions s
INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
INNER JOIN silver.circuits c ON m.circuit_id = c.circuit_id
LEFT JOIN silver.results r ON s.session_id = r.session_id
LEFT JOIN silver.race_control rc ON s.session_id = rc.session_id
LEFT JOIN silver.weather w ON s.session_id = w.session_id
GROUP BY
    m.season,
    m.round_number,
    m.meeting_official_name,
    m.meeting_id,
    c.circuit_id,
    c.circuit_name,
    c.circuit_short_name,
    s.session_id,
    s.session_type,
    s.scheduled_laps,
    s.start_time,
    s.end_time
ORDER BY 
    m.season,
    m.round_number,
    s.start_time;

-- Create indexes on session_summary for performance
CREATE INDEX IF NOT EXISTS idx_session_summary_session 
    ON gold.session_summary(session_id);
CREATE INDEX IF NOT EXISTS idx_session_summary_season 
    ON gold.session_summary(season);
CREATE INDEX IF NOT EXISTS idx_session_summary_session_type 
    ON gold.session_summary(session_type);

-- 6. Lap Times
-- Serves as the canonical per-lap timing table for building race traces, stint analysis, and pace comparisons.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.lap_times AS
SELECT
    m.season,
    m.round_number,
    m.meeting_official_name,
    s.session_type,
    s.session_id,
    l.driver_id,
    dis.driver_number,
    dis.driver_name,
    dis.name_acronym,
    dis.team_id,
    dis.team_name,
    dis.display_name,
    dis.color_hex,
    l.lap_number,
    l.date_start,
    l.lap_duration_ms,
    l.duration_s1_ms,
    l.duration_s2_ms,
    l.duration_s3_ms,
    l.i1_speed_kph,
    l.i2_speed_kph,
    l.st_speed_kph,
    l.is_pit_in_lap,
    l.is_pit_out_lap,
    l.is_valid,
    -- Derived fields
    l.lap_duration_ms / 1000.0 AS lap_time_s,
    SUM(l.lap_duration_ms) OVER (
        PARTITION BY l.session_id, l.driver_id
        ORDER BY l.lap_number
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_time_ms
FROM silver.laps l
INNER JOIN silver.sessions s ON l.session_id = s.session_id
INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
INNER JOIN silver.driver_id_by_session dis 
    ON l.session_id = dis.session_id 
    AND l.driver_id = dis.driver_id
WHERE s.session_type IN ('race', 'sprint')
ORDER BY 
    m.season,
    s.session_id,
    l.driver_id,
    l.lap_number;

-- Create indexes on lap_times for performance
CREATE INDEX IF NOT EXISTS idx_lap_times_session_driver_lap 
    ON gold.lap_times(session_id, driver_id, lap_number);
CREATE INDEX IF NOT EXISTS idx_lap_times_season 
    ON gold.lap_times(season);
CREATE INDEX IF NOT EXISTS idx_lap_times_session_type 
    ON gold.lap_times(session_type);

-- 7. Lap Intervals
-- Adds leader gap and car-to-car interval data at lap granularity for position-by-lap charts.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.lap_intervals AS
WITH laps_with_next_start AS (
    -- Add next lap's date_start to each lap for range matching
    SELECT 
        l.session_id,
        l.driver_id,
        l.lap_number,
        l.date_start,
        LEAD(l.date_start) OVER (
            PARTITION BY l.session_id, l.driver_id 
            ORDER BY l.lap_number
        ) AS next_lap_date_start
    FROM silver.laps l
    INNER JOIN silver.sessions s ON l.session_id = s.session_id
    WHERE s.session_type IN ('race', 'sprint')
),
interval_lap_mapping AS (
    -- For each lap, find the latest interval that falls within its time window
    SELECT DISTINCT ON (l.session_id, l.driver_id, l.lap_number)
        l.session_id,
        l.driver_id,
        l.lap_number,
        i.gap_to_leader_ms,
        i.interval_ms
    FROM laps_with_next_start l
    LEFT JOIN LATERAL (
        SELECT i.gap_to_leader_ms, i.interval_ms
        FROM silver.intervals i
        WHERE i.session_id = l.session_id
          AND i.driver_id = l.driver_id
          AND i.date >= l.date_start
          AND (l.next_lap_date_start IS NULL OR i.date < l.next_lap_date_start)
          AND i.gap_to_leader_ms IS NOT NULL
        ORDER BY i.date DESC
        LIMIT 1
    ) i ON true
    WHERE i.gap_to_leader_ms IS NOT NULL
)
SELECT
    m.season,
    m.round_number,
    m.meeting_official_name,
    s.session_type,
    ilm.session_id,
    ilm.driver_id,
    dis.driver_number,
    dis.driver_name,
    dis.name_acronym,
    dis.team_id,
    dis.team_name,
    dis.display_name,
    dis.color_hex,
    ilm.lap_number,
    ilm.gap_to_leader_ms,
    ilm.interval_ms,
    -- Derived fields
    ilm.gap_to_leader_ms / 1000.0 AS gap_to_leader_s,
    ilm.interval_ms / 1000.0 AS interval_s,
    -- Position derived by ranking gap_to_leader_ms per (session_id, lap_number)
    DENSE_RANK() OVER (
        PARTITION BY ilm.session_id, ilm.lap_number
        ORDER BY ilm.gap_to_leader_ms NULLS LAST
    ) AS position
FROM interval_lap_mapping ilm
INNER JOIN silver.sessions s ON ilm.session_id = s.session_id
INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
INNER JOIN silver.driver_id_by_session dis 
    ON ilm.session_id = dis.session_id 
    AND ilm.driver_id = dis.driver_id
ORDER BY 
    m.season,
    ilm.session_id,
    ilm.lap_number,
    position;

-- Create indexes on lap_intervals for performance
CREATE INDEX IF NOT EXISTS idx_lap_intervals_session_driver_lap 
    ON gold.lap_intervals(session_id, driver_id, lap_number);
CREATE INDEX IF NOT EXISTS idx_lap_intervals_season 
    ON gold.lap_intervals(season);
CREATE INDEX IF NOT EXISTS idx_lap_intervals_session_type 
    ON gold.lap_intervals(session_type);

-- 8. Drivers Dimension
-- Dimension table for driver identities and season-specific attributes (number, primary team, nationality, headshot/branding).
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.dim_drivers AS
WITH driver_seasons AS (
    -- Get all unique (driver_id, season) combinations from driver_id_by_session
    SELECT DISTINCT 
        dis.driver_id,
        dis.season
    FROM silver.driver_id_by_session dis
),
driver_season_teams AS (
    -- Get primary team for each driver/season from most recent session
    SELECT DISTINCT ON (dis.driver_id, dis.season)
        dis.driver_id,
        dis.season,
        dis.team_id AS primary_team_id,
        dis.team_name AS primary_team_name
    FROM silver.driver_id_by_session dis
    INNER JOIN silver.sessions s ON dis.session_id = s.session_id
    WHERE dis.team_id IS NOT NULL
    ORDER BY dis.driver_id, dis.season, s.start_time DESC
)
SELECT
    d.driver_id,
    dns.driver_number,
    d.full_name,
    d.name_acronym,
    d.country_code,
    d.headshot_url,
    d.headshot_override,
    d.wikipedia_id AS wikipedia_url,
    d.birthdate,
    ds.season,
    dst.primary_team_id,
    dst.primary_team_name
FROM driver_seasons ds
INNER JOIN silver.drivers d ON ds.driver_id = d.driver_id
INNER JOIN silver.driver_numbers_by_season dns 
    ON ds.driver_id = dns.driver_id 
    AND ds.season = dns.season
LEFT JOIN driver_season_teams dst 
    ON ds.driver_id = dst.driver_id 
    AND ds.season = dst.season
ORDER BY ds.season, d.driver_id;

-- Create indexes on dim_drivers for performance
CREATE INDEX IF NOT EXISTS idx_dim_drivers_driver_id 
    ON gold.dim_drivers(driver_id);
CREATE INDEX IF NOT EXISTS idx_dim_drivers_season 
    ON gold.dim_drivers(season);
CREATE INDEX IF NOT EXISTS idx_dim_drivers_driver_season 
    ON gold.dim_drivers(driver_id, season);

-- 9. Teams Dimension
-- Dimension table for team identities and branding over time, including display names, colors, and logos.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.dim_teams AS
SELECT
    t.team_id,
    tb.team_name,
    tb.display_name,
    tb.color_hex,
    tb.logo_url,
    tb.season
FROM silver.teams t
INNER JOIN silver.team_branding tb ON t.team_id = tb.team_id
ORDER BY tb.season, t.team_id;

-- Create indexes on dim_teams for performance
CREATE INDEX IF NOT EXISTS idx_dim_teams_team_id 
    ON gold.dim_teams(team_id);
CREATE INDEX IF NOT EXISTS idx_dim_teams_season 
    ON gold.dim_teams(season);
CREATE INDEX IF NOT EXISTS idx_dim_teams_team_season 
    ON gold.dim_teams(team_id, season);

-- 10. Meetings Dimension
-- Dimension table for grands prix / meetings, combining season, round, circuit, and country/location metadata.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.dim_meetings AS
SELECT
    m.meeting_id,
    m.season,
    m.round_number,
    m.meeting_official_name,
    m.meeting_name AS meeting_short_name,
    m.circuit_id,
    c.circuit_name,
    c.circuit_short_name,
    c.location,
    c.country_code,
    co.country_name,
    co.flag_url,
    m.date_start,
    COALESCE(m.date_end, (
        SELECT MAX(s.start_time)
        FROM silver.sessions s
        WHERE s.meeting_id = m.meeting_id
    )) AS date_end
FROM silver.meetings m
INNER JOIN silver.circuits c ON m.circuit_id = c.circuit_id
INNER JOIN silver.countries co ON c.country_code = co.country_code
ORDER BY m.season, m.round_number;

-- Create indexes on dim_meetings for performance
CREATE INDEX IF NOT EXISTS idx_dim_meetings_meeting_id 
    ON gold.dim_meetings(meeting_id);
CREATE INDEX IF NOT EXISTS idx_dim_meetings_season 
    ON gold.dim_meetings(season);
CREATE INDEX IF NOT EXISTS idx_dim_meetings_season_meeting 
    ON gold.dim_meetings(season, meeting_id);

-- 11. Circuits Dimension
-- Dimension table for circuits, combining circuit characteristics, geography, lap records, and usage stats.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.dim_circuits AS
WITH circuit_meetings AS (
    -- Get meeting stats per circuit
    SELECT 
        c.circuit_id,
        MAX(m.season) AS last_year_used,
        MAX(m.season) FILTER (WHERE EXISTS (
            SELECT 1 FROM silver.sessions s 
            WHERE s.meeting_id = m.meeting_id 
            AND s.session_type IN ('race', 'sprint')
        )) AS last_race_season,
        (SELECT s.session_id 
         FROM silver.sessions s
         INNER JOIN silver.meetings m2 ON s.meeting_id = m2.meeting_id
         WHERE m2.circuit_id = c.circuit_id
           AND s.session_type = 'race'
         ORDER BY m2.season DESC, s.start_time DESC
         LIMIT 1) AS last_race_session_id,
        (SELECT m3.meeting_id
         FROM silver.meetings m3
         WHERE m3.circuit_id = c.circuit_id
         ORDER BY m3.season DESC, m3.date_start DESC
         LIMIT 1) AS last_meeting_id
    FROM silver.circuits c
    LEFT JOIN silver.meetings m ON c.circuit_id = m.circuit_id
    GROUP BY c.circuit_id
),
circuit_turns AS (
    -- Count turns per circuit from silver.turns
    SELECT 
        circuit_id,
        COUNT(*) AS total_turns
    FROM silver.turns
    GROUP BY circuit_id
)
SELECT
    -- Identity & geography
    c.circuit_id,
    c.circuit_name,
    c.circuit_short_name,
    c.location,
    c.country_code,
    co.country_name,
    co.flag_url,
    c.lat,
    c.lon,
    -- Circuit characteristics
    c.lap_length_km,
    c.race_laps,
    (c.race_laps * c.lap_length_km) AS race_distance_km,
    c.sprint_laps,
    (c.sprint_laps * c.lap_length_km) AS sprint_distance_km,
    cm.last_year_used,
    ct.total_turns,
    c.circuit_svg,
    -- Lap record info
    c.fastest_lap_time_ms,
    c.fastest_lap_driver_id,
    d.full_name AS fastest_lap_driver_name,
    d.name_acronym AS fastest_lap_driver_name_acronym,
    c.fastest_lap_year,
    -- Usage stats
    cm.last_race_season,
    cm.last_race_session_id,
    cm.last_meeting_id
FROM silver.circuits c
INNER JOIN silver.countries co ON c.country_code = co.country_code
LEFT JOIN circuit_meetings cm ON c.circuit_id = cm.circuit_id
LEFT JOIN circuit_turns ct ON c.circuit_id = ct.circuit_id
LEFT JOIN silver.drivers d ON c.fastest_lap_driver_id = d.driver_id
ORDER BY c.circuit_id;

-- Create indexes on dim_circuits for performance
CREATE INDEX IF NOT EXISTS idx_dim_circuits_circuit_id 
    ON gold.dim_circuits(circuit_id);
CREATE INDEX IF NOT EXISTS idx_dim_circuits_country_code 
    ON gold.dim_circuits(country_code);

-- 12. Circuit Overtake Stats
-- A view of session summary which focuses on aggregate statistics for a given circuit.
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.circuit_overtake_stats AS
WITH circuit_sessions AS (
    -- Join session_summary to get circuit_id
    SELECT 
        ss.circuit_name,
        c.circuit_id,
        ss.session_type,
        ss.overtakes_count
    FROM gold.session_summary ss
    INNER JOIN silver.sessions s ON ss.session_id = s.session_id
    INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
    INNER JOIN silver.circuits c ON m.circuit_id = c.circuit_id
    WHERE ss.session_type IN ('race', 'sprint')
      AND ss.overtakes_count IS NOT NULL
)
SELECT
    c.circuit_id,
    c.circuit_name,
    -- Average overtakes per race
    ROUND(AVG(cs.overtakes_count) FILTER (WHERE cs.session_type = 'race'), 2) AS overtakes_race_avg,
    -- Average overtakes per sprint
    ROUND(AVG(cs.overtakes_count) FILTER (WHERE cs.session_type = 'sprint'), 2) AS overtakes_sprint_avg,
    -- Record highest overtakes in a race
    MAX(cs.overtakes_count) FILTER (WHERE cs.session_type = 'race') AS overtakes_race_record,
    -- Record highest overtakes in a sprint
    MAX(cs.overtakes_count) FILTER (WHERE cs.session_type = 'sprint') AS overtakes_sprint_record
FROM silver.circuits c
INNER JOIN circuit_sessions cs ON c.circuit_id = cs.circuit_id
GROUP BY c.circuit_id, c.circuit_name
ORDER BY c.circuit_name;

-- Create indexes on circuit_overtake_stats for performance
CREATE INDEX IF NOT EXISTS idx_circuit_overtake_stats_circuit_id 
    ON gold.circuit_overtake_stats(circuit_id);

