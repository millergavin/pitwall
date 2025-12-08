-- Gold layer: Telemetry Trace (TEST VERSION - Limited Data)
-- Test version with limited data for faster execution
-- Exposes high-frequency car telemetry samples aligned with GPS and lap context

-- Drop existing test view if it exists
DROP MATERIALIZED VIEW IF EXISTS gold.telemetry_trace_test;

CREATE MATERIALIZED VIEW gold.telemetry_trace_test AS
WITH limited_sessions AS (
    -- Limit to 5 sessions that have telemetry data for testing
    SELECT s.session_id
    FROM silver.sessions s
    INNER JOIN silver.car_telemetry ct ON s.session_id = ct.session_id
    WHERE s.session_type IN ('race', 'sprint', 'quali', 'sprint_quali')
    GROUP BY s.session_id, s.start_time
    ORDER BY s.start_time DESC
    LIMIT 5
),
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
run_terminal_cmd
laps_with_end AS (
    -- Calculate lap end time from next lap's start or lap duration
    SELECT 
        l.session_id,
        l.driver_id,
        l.lap_id,
        l.lap_number,
        l.date_start,
        COALESCE(
            LEAD(l.date_start) OVER (
                PARTITION BY l.session_id, l.driver_id 
                ORDER BY l.lap_number
            ),
            CASE 
                WHEN l.lap_duration_ms IS NOT NULL 
                THEN l.date_start + (l.lap_duration_ms || ' milliseconds')::INTERVAL
                ELSE l.date_start + INTERVAL '2 minutes'  -- Fallback for missing duration
            END
        ) AS date_end
    FROM silver.laps l
    INNER JOIN silver.sessions s ON l.session_id = s.session_id
    INNER JOIN limited_sessions ls ON l.session_id = ls.session_id
    WHERE s.session_type IN ('race', 'sprint', 'quali', 'sprint_quali')
),
telemetry_with_gps AS (
    -- Join telemetry with GPS using nearest timestamp match (within 0.3s)
    -- Limit to 100k samples per session for testing
    SELECT DISTINCT ON (ct.car_telemetry_id)
        ct.car_telemetry_id,
        ct.session_id,
        ct.driver_id,
        ct.date AS sample_timestamp,
        ct.drs,
        ct.n_gear,
        ct.rpm,
        ct.speed_kph,
        ct.throttle,
        ct.brake,
        cg.x,
        cg.y,
        cg.z
    FROM silver.car_telemetry ct
    INNER JOIN silver.sessions s ON ct.session_id = s.session_id
    INNER JOIN limited_sessions ls ON ct.session_id = ls.session_id
    LEFT JOIN LATERAL (
        SELECT cg.x, cg.y, cg.z
        FROM silver.car_gps cg
        WHERE cg.session_id = ct.session_id
          AND cg.driver_id = ct.driver_id
          AND ABS(EXTRACT(EPOCH FROM (ct.date - cg.date))) < 0.3
        ORDER BY ABS(EXTRACT(EPOCH FROM (ct.date - cg.date)))
        LIMIT 1
    ) cg ON true
    WHERE s.session_type IN ('race', 'sprint', 'quali', 'sprint_quali')
    LIMIT 500000  -- Limit total samples for testing
),
telemetry_with_lap AS (
    -- Map telemetry samples to lap context
    SELECT DISTINCT ON (twg.car_telemetry_id)
        twg.*,
        lwe.lap_id,
        lwe.lap_number
    FROM telemetry_with_gps twg
    LEFT JOIN LATERAL (
        SELECT lwe.lap_id, lwe.lap_number
        FROM laps_with_end lwe
        WHERE lwe.session_id = twg.session_id
          AND lwe.driver_id = twg.driver_id
          AND twg.sample_timestamp >= lwe.date_start
          AND twg.sample_timestamp < lwe.date_end
        LIMIT 1
    ) lwe ON true
),
pit_stop_session_stats AS (
    -- Calculate session-level pit stop statistics for derived flags
    SELECT 
        ps.session_id,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ps.pit_duration_ms) AS median_pit_duration_ms,
        PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM ps.date)) AS early_pit_threshold_epoch,
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM ps.date)) AS late_pit_threshold_epoch
    FROM silver.pit_stops ps
    INNER JOIN silver.sessions s ON ps.session_id = s.session_id
    INNER JOIN limited_sessions ls ON ps.session_id = ls.session_id
    WHERE s.session_type IN ('race', 'sprint')
      AND ps.pit_duration_ms IS NOT NULL
    GROUP BY ps.session_id
),
pit_stop_data AS (
    -- Get pit stop data with session statistics
    SELECT 
        ps.session_id,
        ps.driver_id,
        ps.lap_number,
        ps.date AS pit_date,
        ps.pit_duration_ms,
        psss.median_pit_duration_ms,
        to_timestamp(psss.early_pit_threshold_epoch) AS early_pit_threshold,
        to_timestamp(psss.late_pit_threshold_epoch) AS late_pit_threshold
    FROM silver.pit_stops ps
    INNER JOIN silver.sessions s ON ps.session_id = s.session_id
    INNER JOIN limited_sessions ls ON ps.session_id = ls.session_id
    LEFT JOIN pit_stop_session_stats psss ON ps.session_id = psss.session_id
    WHERE s.session_type IN ('race', 'sprint')
)
SELECT
    -- Meeting metadata
    m.season,
    m.round_number,
    m.meeting_official_name,
    c.circuit_name,
    s.session_type,
    
    -- Session and sample identifiers
    twl.session_id,
    twl.driver_id,
    dis.driver_number,
    dis.driver_name,
    dis.name_acronym,
    dis.team_id,
    dis.team_name,
    dis.display_name,
    dis.color_hex,
    twl.sample_timestamp,
    
    -- Lap context
    twl.lap_id,
    twl.lap_number,
    
    -- Telemetry data
    twl.drs,
    twl.n_gear,
    twl.rpm,
    twl.speed_kph,
    twl.throttle,
    twl.brake,
    
    -- GPS coordinates
    twl.x,
    twl.y,
    twl.z,
    
    -- Pit stop data (from lap context)
    psd.pit_date,
    psd.pit_duration_ms,
    
    -- Derived flags
    CASE 
        WHEN psd.pit_duration_ms IS NOT NULL 
             AND psd.pit_duration_ms > psd.median_pit_duration_ms 
        THEN true 
        ELSE false 
    END AS is_slow_stop,
    CASE 
        WHEN psd.pit_date IS NOT NULL 
             AND psd.pit_date <= psd.early_pit_threshold 
        THEN true 
        ELSE false 
    END AS is_early_stop,
    CASE 
        WHEN psd.pit_date IS NOT NULL 
             AND psd.pit_date >= psd.late_pit_threshold 
        THEN true 
        ELSE false 
    END AS is_late_stop
FROM telemetry_with_lap twl
INNER JOIN silver.sessions s ON twl.session_id = s.session_id
INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
INNER JOIN silver.circuits c ON m.circuit_id = c.circuit_id
INNER JOIN silver.driver_id_by_session dis 
    ON twl.session_id = dis.session_id 
    AND twl.driver_id = dis.driver_id
LEFT JOIN pit_stop_data psd 
    ON twl.session_id = psd.session_id 
    AND twl.driver_id = psd.driver_id 
    AND twl.lap_number = psd.lap_number
WHERE s.session_type IN ('race', 'sprint', 'quali', 'sprint_quali')
ORDER BY 
    m.season,
    twl.session_id,
    twl.driver_id,
    twl.sample_timestamp;

-- Create indexes on telemetry_trace_test for performance
CREATE INDEX IF NOT EXISTS idx_telemetry_trace_test_session_driver_timestamp 
    ON gold.telemetry_trace_test(session_id, driver_id, sample_timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_trace_test_session_lap 
    ON gold.telemetry_trace_test(session_id, lap_number);
CREATE INDEX IF NOT EXISTS idx_telemetry_trace_test_season 
    ON gold.telemetry_trace_test(season);

