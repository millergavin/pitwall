-- Silver layer tables
-- These tables contain cleaned, validated, and enriched data from the bronze layer

-- 1. countries
CREATE TABLE IF NOT EXISTS silver.countries (
    country_code CHAR(3) NOT NULL PRIMARY KEY,
    country_name TEXT NOT NULL,
    alpha2 CHAR(2),
    numeric_code INT,
    lat_avg NUMERIC(9,6) NOT NULL,
    lon_avg NUMERIC(9,6) NOT NULL,
    demonym TEXT,
    emoji_flag TEXT,
    flag_url TEXT
);

-- 2. country_code_alias
CREATE TABLE IF NOT EXISTS silver.country_code_alias (
    alias TEXT NOT NULL PRIMARY KEY,
    country_code CHAR(3) NOT NULL REFERENCES silver.countries(country_code)
);

-- 3. circuits
CREATE TABLE IF NOT EXISTS silver.circuits (
    circuit_id TEXT NOT NULL PRIMARY KEY,
    openf1_circuit_key TEXT NOT NULL,
    circuit_short_name TEXT NOT NULL,
    country_code CHAR(3) NOT NULL REFERENCES silver.countries(country_code),
    location TEXT,
    lat NUMERIC(9,6),
    lon NUMERIC(9,6),
    timezone_tzid TEXT,
    circuit_name TEXT,
    lap_length_km NUMERIC(6,3),
    fastest_lap_time_ms INT,
    fastest_lap_driver_id TEXT,
    fastest_lap_year INT,
    circuit_svg TEXT,
    race_laps INT,
    sprint_laps INT
);

-- 4. meetings
-- Note: openf1_meeting_key is nullable to allow future/scheduled meetings to be
-- inserted before OpenF1 has data for them. When data is later ingested, the
-- upsert will match on meeting_id and fill in the openf1_meeting_key.
CREATE TABLE IF NOT EXISTS silver.meetings (
    meeting_id TEXT NOT NULL PRIMARY KEY,
    openf1_meeting_key TEXT,  -- NULL for future meetings until data is ingested
    circuit_id TEXT NOT NULL REFERENCES silver.circuits(circuit_id),
    meeting_name TEXT NOT NULL,
    season INT NOT NULL,
    meeting_official_name TEXT,
    date_start TIMESTAMPTZ NOT NULL,
    date_end TIMESTAMPTZ,
    round_number INT
);

-- Ensure openf1_meeting_key is unique when present (partial unique index)
CREATE UNIQUE INDEX IF NOT EXISTS idx_meetings_openf1_meeting_key_unique 
ON silver.meetings(openf1_meeting_key) 
WHERE openf1_meeting_key IS NOT NULL;

-- Create ENUM types
DO $$ BEGIN
    CREATE TYPE silver.session_type_enum AS ENUM ('p1', 'p2', 'p3', 'quali', 'sprint_quali', 'sprint', 'race');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE silver.points_awarding_enum AS ENUM ('none', 'sprint', 'race');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE silver.completion_band_enum AS ENUM ('0_to_25_PCT', '25_to_50_PCT', '50_to_75_PCT', '100_PCT');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE silver.status_enum AS ENUM ('dns', 'dnf', 'dsq', 'finished', 'nc');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE silver.bonus_enum AS ENUM ('fastest_lap');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 5. sessions
CREATE TABLE IF NOT EXISTS silver.sessions (
    session_id TEXT NOT NULL PRIMARY KEY,
    meeting_id TEXT NOT NULL REFERENCES silver.meetings(meeting_id),
    openf1_session_key TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    session_name TEXT NOT NULL,
    session_type silver.session_type_enum,
    scheduled_laps INT,
    completed_laps INT,
    points_awarding silver.points_awarding_enum NOT NULL DEFAULT 'none',
    duration_min INT
);

-- 6. teams
CREATE TABLE IF NOT EXISTS silver.teams (
    team_id TEXT NOT NULL PRIMARY KEY
);

-- 7. team_branding
CREATE TABLE IF NOT EXISTS silver.team_branding (
    team_id TEXT NOT NULL REFERENCES silver.teams(team_id),
    team_name TEXT NOT NULL,
    season INT NOT NULL,
    color_hex TEXT NOT NULL,
    display_name TEXT,
    logo_url TEXT,
    PRIMARY KEY (team_id, team_name, season)
);

-- 8. team_alias
CREATE TABLE IF NOT EXISTS silver.team_alias (
    alias TEXT NOT NULL PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES silver.teams(team_id)
);

-- 9. drivers
CREATE TABLE IF NOT EXISTS silver.drivers (
    driver_id TEXT NOT NULL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    full_name TEXT,
    name_acronym CHAR(3) NOT NULL,
    country_code CHAR(3) REFERENCES silver.countries(country_code),
    headshot_url TEXT,
    headshot_override TEXT,
    wikipedia_id TEXT,
    birthdate TIMESTAMPTZ
);

-- 10. driver_numbers_by_season
CREATE TABLE IF NOT EXISTS silver.driver_numbers_by_season (
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    season INT NOT NULL,
    driver_number INT NOT NULL,
    PRIMARY KEY (driver_id, season)
);

-- 11. driver_teams_by_session
CREATE TABLE IF NOT EXISTS silver.driver_teams_by_session (
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    team_id TEXT NOT NULL REFERENCES silver.teams(team_id),
    PRIMARY KEY (session_id, driver_id)
);

-- 12. driver_alias
CREATE TABLE IF NOT EXISTS silver.driver_alias (
    alias TEXT NOT NULL PRIMARY KEY,
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id)
);

-- 13. race_control
CREATE TABLE IF NOT EXISTS silver.race_control (
    message_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    category TEXT NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    driver_id TEXT REFERENCES silver.drivers(driver_id),
    flag TEXT,
    lap_number INT,
    message TEXT,
    scope TEXT,
    referenced_lap INT,
    referenced_lap_id BIGINT REFERENCES silver.laps(lap_id)
);

-- 14. laps
CREATE TABLE IF NOT EXISTS silver.laps (
    lap_id BIGINT NOT NULL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    lap_number INT NOT NULL,
    date_start TIMESTAMPTZ NOT NULL,
    lap_duration_ms INT,
    duration_s1_ms INT,
    duration_s2_ms INT,
    duration_s3_ms INT,
    i1_speed_kph NUMERIC(6,2),
    i2_speed_kph NUMERIC(6,2),
    st_speed_kph NUMERIC(6,2),
    is_pit_out_lap BOOLEAN,
    s1_segments JSONB,
    s2_segments JSONB,
    s3_segments JSONB,
    is_pit_in_lap BOOLEAN NOT NULL,
    is_valid BOOLEAN NOT NULL
);

-- 15. car_telemetry
CREATE TABLE IF NOT EXISTS silver.car_telemetry (
    car_telemetry_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    date TIMESTAMPTZ NOT NULL,
    drs INT,
    n_gear INT,
    rpm INT,
    speed_kph INT,
    throttle INT,
    brake INT
);

-- 16. car_gps
CREATE TABLE IF NOT EXISTS silver.car_gps (
    car_gps_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    date TIMESTAMPTZ NOT NULL,
    x INT,
    y INT,
    z INT
);

-- Create ENUM type for tyre compound
DO $$ BEGIN
    CREATE TYPE silver.tyre_compound_enum AS ENUM ('soft', 'medium', 'hard', 'intermediate', 'wet');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 17. position
CREATE TABLE IF NOT EXISTS silver.position (
    position_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    date TIMESTAMPTZ NOT NULL,
    position INT
);

-- 18. intervals
CREATE TABLE IF NOT EXISTS silver.intervals (
    interval_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    date TIMESTAMPTZ NOT NULL,
    gap_to_leader_ms INT,
    interval_ms INT
);

-- 19. overtakes
CREATE TABLE IF NOT EXISTS silver.overtakes (
    overtake_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    overtaken_driver_id TEXT REFERENCES silver.drivers(driver_id),
    overtaking_driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    position INT NOT NULL,
    date TIMESTAMPTZ NOT NULL
);

-- 20. pit_stops
CREATE TABLE IF NOT EXISTS silver.pit_stops (
    pit_stop_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    date TIMESTAMPTZ NOT NULL,
    lap_number INT NOT NULL,
    lap_id BIGINT NOT NULL REFERENCES silver.laps(lap_id),
    pit_duration_ms INT
);

-- 21. stints
CREATE TABLE IF NOT EXISTS silver.stints (
    stint_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    lap_start INT NOT NULL,
    lap_start_id BIGINT NOT NULL REFERENCES silver.laps(lap_id),
    lap_end INT,
    lap_end_id BIGINT REFERENCES silver.laps(lap_id),
    tyre_age_at_start INT,
    tyre_compound silver.tyre_compound_enum,
    stint_number INT
);

-- 22. weather
CREATE TABLE IF NOT EXISTS silver.weather (
    weather_id TEXT NOT NULL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    date TIMESTAMPTZ NOT NULL,
    air_temp_c NUMERIC(6,3),
    track_temp_c NUMERIC(6,3),
    humidity INT,
    rainfall INT,
    pressure_mbar NUMERIC(7,3),
    wind_direction INT,
    wind_speed_mps NUMERIC(6,3)
);

-- 23. results
CREATE TABLE IF NOT EXISTS silver.results (
    session_id TEXT NOT NULL REFERENCES silver.sessions(session_id),
    driver_id TEXT NOT NULL REFERENCES silver.drivers(driver_id),
    finish_position INT,
    gap_to_leader_ms INT,
    duration_ms INT,
    laps_completed INT,
    status silver.status_enum NOT NULL,
    points NUMERIC(5,2) NOT NULL,
    best_lap_ms INT,
    fastest_lap BOOLEAN NOT NULL,
    grid_position INT,
    quali_lap_ms INT,
    PRIMARY KEY (session_id, driver_id)
);

-- 24. completion_band
CREATE TABLE IF NOT EXISTS silver.completion_band (
    completion_band silver.completion_band_enum PRIMARY KEY,
    range_represented TEXT,
    shorthand TEXT,
    notes TEXT
);

-- 25. points_system
CREATE TABLE IF NOT EXISTS silver.points_system (
    points_id TEXT NOT NULL PRIMARY KEY,
    season INT NOT NULL,
    race_type silver.points_awarding_enum NOT NULL,
    completion_band silver.completion_band_enum NOT NULL,
    position INT,
    bonus silver.bonus_enum,
    points NUMERIC(4,1) NOT NULL
);


-- 26. images
-- Generic media table for all images (circuits, drivers, teams, races)
-- One image can be associated with multiple entities via arrays
CREATE TABLE IF NOT EXISTS silver.images (
    image_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    
    -- Display metadata
    is_cover BOOLEAN NOT NULL DEFAULT FALSE,    -- Hero/cover image
    image_type TEXT DEFAULT 'general',          -- 'action', 'portrait', 'podium', 'destination', 'historical', etc.
    caption TEXT,                               -- Description of the image
    credit TEXT,                                -- Photographer/source attribution
    year INT,                                   -- Year photo was taken
    display_order INT DEFAULT 0,                -- For ordering in galleries
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Entity associations (all nullable - image might relate to any/all)
    circuit_id TEXT REFERENCES silver.circuits(circuit_id),
    driver_ids TEXT[],                          -- Array: ['lewis-hamilton', 'max-verstappen']
    team_ids TEXT[],                            -- Array: ['mercedes', 'red-bull']
    meeting_id TEXT REFERENCES silver.meetings(meeting_id),
    
    -- Free-form tags
    tags TEXT[]                                 -- ['2024', 'wet-race', 'crash', 'celebration']
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_images_circuit_id ON silver.images(circuit_id);
CREATE INDEX IF NOT EXISTS idx_images_is_cover ON silver.images(is_cover) WHERE is_cover = TRUE;
CREATE INDEX IF NOT EXISTS idx_images_type ON silver.images(image_type);
CREATE INDEX IF NOT EXISTS idx_images_driver_ids ON silver.images USING GIN(driver_ids);
CREATE INDEX IF NOT EXISTS idx_images_team_ids ON silver.images USING GIN(team_ids);
CREATE INDEX IF NOT EXISTS idx_images_tags ON silver.images USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_images_year ON silver.images(year);
