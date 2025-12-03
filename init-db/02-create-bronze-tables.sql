-- Create bronze tables for raw data ingestion
-- All columns are TEXT (nullable) except ingested_at which is TIMESTAMPTZ (NOT NULL)

-- 1. meetings_raw
CREATE TABLE IF NOT EXISTS bronze.meetings_raw (
    openf1_circuit_key TEXT,
    circuit_short_name TEXT,
    country_code TEXT,
    location TEXT,
    gmt_offset TEXT,
    country_name TEXT,
    country_key TEXT,
    meeting_name TEXT,
    season TEXT,
    meeting_official_name TEXT,
    date_start TEXT,
    openf1_meeting_key TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 2. sessions_raw
CREATE TABLE IF NOT EXISTS bronze.sessions_raw (
    openf1_meeting_key TEXT,
    openf1_session_key TEXT,
    date_start TEXT,
    date_end TEXT,
    session_name TEXT,
    openf1_circuit_key TEXT,
    circuit_short_name TEXT,
    country_code TEXT,
    country_key TEXT,
    country_name TEXT,
    gmt_offset TEXT,
    location TEXT,
    session_type TEXT,
    year TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 3. results_raw
CREATE TABLE IF NOT EXISTS bronze.results_raw (
    openf1_session_key TEXT,
    driver_number TEXT,
    position TEXT,
    gap_to_leader_s TEXT,
    duration_s TEXT,
    laps_completed TEXT,
    dnf TEXT,
    dns TEXT,
    dsq TEXT,
    openf1_meeting_key TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 4. laps_raw
CREATE TABLE IF NOT EXISTS bronze.laps_raw (
    openf1_session_key TEXT,
    driver_number TEXT,
    lap_number TEXT,
    date_start TEXT,
    lap_duration_s TEXT,
    duration_s1_s TEXT,
    duration_s2_s TEXT,
    duration_s3_s TEXT,
    i1_speed_kph TEXT,
    i2_speed_kph TEXT,
    st_speed_kph TEXT,
    is_pit_out_lap TEXT,
    s1_segments TEXT,
    s2_segments TEXT,
    s3_segments TEXT,
    openf1_meeting_key TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 5. drivers_raw
CREATE TABLE IF NOT EXISTS bronze.drivers_raw (
    broadcast_name TEXT,
    team_name TEXT,
    team_color_hex TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    name_acronym TEXT,
    country_code TEXT,
    headshot_url TEXT,
    openf1_session_key TEXT,
    openf1_meeting_key TEXT,
    driver_number TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 6. race_control_raw
CREATE TABLE IF NOT EXISTS bronze.race_control_raw (
    openf1_session_key TEXT,
    category TEXT,
    date TEXT,
    driver_number TEXT,
    flag TEXT,
    lap_number TEXT,
    message TEXT,
    scope TEXT,
    sector TEXT,
    openf1_meeting_key TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 7. starting_grid_raw
CREATE TABLE IF NOT EXISTS bronze.starting_grid_raw (
    openf1_session_key TEXT,
    driver_number TEXT,
    position TEXT,
    lap_duration_s TEXT,
    openf1_meeting_key TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 8. weather_raw
CREATE TABLE IF NOT EXISTS bronze.weather_raw (
    openf1_meeting_key TEXT,
    openf1_session_key TEXT,
    date TEXT,
    air_temp_c TEXT,
    humidity TEXT,
    pressure TEXT,
    rainfall TEXT,
    track_temp_c TEXT,
    wind_direction TEXT,
    wind_speed_mps TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 9. car_telemetry_raw
CREATE TABLE IF NOT EXISTS bronze.car_telemetry_raw (
    openf1_meeting_key TEXT,
    openf1_session_key TEXT,
    date TEXT,
    driver_number TEXT,
    brake TEXT,
    drs TEXT,
    n_gear TEXT,
    rpm TEXT,
    speed_kph TEXT,
    throttle TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 10. car_gps_raw
CREATE TABLE IF NOT EXISTS bronze.car_gps_raw (
    openf1_meeting_key TEXT,
    openf1_session_key TEXT,
    date TEXT,
    driver_number TEXT,
    x TEXT,
    y TEXT,
    z TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 11. overtakes_raw
CREATE TABLE IF NOT EXISTS bronze.overtakes_raw (
    openf1_meeting_key TEXT,
    openf1_session_key TEXT,
    date TEXT,
    overtaken_driver_number TEXT,
    overtaking_driver_number TEXT,
    position TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 12. intervals_raw
CREATE TABLE IF NOT EXISTS bronze.intervals_raw (
    openf1_meeting_key TEXT,
    openf1_session_key TEXT,
    driver_number TEXT,
    date TEXT,
    gap_to_leader_s TEXT,
    interval_s TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 13. position_raw
CREATE TABLE IF NOT EXISTS bronze.position_raw (
    openf1_meeting_key TEXT,
    openf1_session_key TEXT,
    driver_number TEXT,
    date TEXT,
    position TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 14. stints_raw
CREATE TABLE IF NOT EXISTS bronze.stints_raw (
    openf1_meeting_key TEXT,
    openf1_session_key TEXT,
    driver_number TEXT,
    stint_number TEXT,
    lap_start TEXT,
    lap_end TEXT,
    compound TEXT,
    tyre_age_at_start TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

-- 15. pit_stops_raw
CREATE TABLE IF NOT EXISTS bronze.pit_stops_raw (
    openf1_meeting_key TEXT,
    openf1_session_key TEXT,
    driver_number TEXT,
    date TEXT,
    lap_number TEXT,
    pit_duration_s TEXT,
    ingested_at TIMESTAMPTZ NOT NULL
);

