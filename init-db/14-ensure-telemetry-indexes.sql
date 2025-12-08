-- Ensure indexes exist on source tables for telemetry_trace view performance
-- These indexes are critical for the LATERAL joins and timestamp matching

-- Indexes on car_telemetry for GPS matching
CREATE INDEX IF NOT EXISTS idx_car_telemetry_session_driver_date 
    ON silver.car_telemetry(session_id, driver_id, date);

CREATE INDEX IF NOT EXISTS idx_car_telemetry_date 
    ON silver.car_telemetry(date);

-- Indexes on car_gps for timestamp matching
CREATE INDEX IF NOT EXISTS idx_car_gps_session_driver_date 
    ON silver.car_gps(session_id, driver_id, date);

CREATE INDEX IF NOT EXISTS idx_car_gps_date 
    ON silver.car_gps(date);

-- Indexes on laps for lap context mapping
CREATE INDEX IF NOT EXISTS idx_laps_session_driver_lap 
    ON silver.laps(session_id, driver_id, lap_number);

CREATE INDEX IF NOT EXISTS idx_laps_session_driver_date_start 
    ON silver.laps(session_id, driver_id, date_start);

-- Indexes on pit_stops for pit stop data joins
CREATE INDEX IF NOT EXISTS idx_pit_stops_session_driver_lap 
    ON silver.pit_stops(session_id, driver_id, lap_number);

CREATE INDEX IF NOT EXISTS idx_pit_stops_session_date 
    ON silver.pit_stops(session_id, date);

-- Indexes on sessions for filtering
CREATE INDEX IF NOT EXISTS idx_sessions_session_type 
    ON silver.sessions(session_type) WHERE session_type IN ('race', 'sprint', 'quali', 'sprint_quali');

