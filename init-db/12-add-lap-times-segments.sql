-- Migration: add sector segment data to gold.lap_times from silver.laps

DROP MATERIALIZED VIEW IF EXISTS gold.lap_times;

CREATE MATERIALIZED VIEW gold.lap_times AS
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
    l.s1_segments,
    l.s2_segments,
    l.s3_segments,
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

CREATE INDEX IF NOT EXISTS idx_lap_times_session_driver_lap 
    ON gold.lap_times(session_id, driver_id, lap_number);
CREATE INDEX IF NOT EXISTS idx_lap_times_season 
    ON gold.lap_times(season);
CREATE INDEX IF NOT EXISTS idx_lap_times_session_type 
    ON gold.lap_times(session_type);

