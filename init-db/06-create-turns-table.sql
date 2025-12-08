-- Silver layer: Turns table
-- Stores turn/corner data for each circuit, used for:
-- - Mapping turns on track SVG overlays
-- - Overlaying turns on telemetry graphs
-- - Circuit stats (turn count, turn types)
-- - Turn-by-turn analysis

-- Create ENUM for turn direction
DO $$ BEGIN
    CREATE TYPE silver.turn_direction_enum AS ENUM ('left', 'right', 'straight');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create ENUM for turn character (how technical/challenging)
DO $$ BEGIN
    CREATE TYPE silver.turn_character_enum AS ENUM ('flat_out', 'lift', 'braking', 'heavy_braking', 'hairpin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create ENUM for overtaking opportunity rating
DO $$ BEGIN
    CREATE TYPE silver.overtaking_rating_enum AS ENUM ('none', 'low', 'medium', 'high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 27. turns
-- Circuit turn/corner reference data
CREATE TABLE IF NOT EXISTS silver.turns (
    turn_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circuit_id TEXT NOT NULL REFERENCES silver.circuits(circuit_id),
    turn_number INT NOT NULL,
    
    -- Position on track
    track_distance_m NUMERIC(8,2),              -- Distance from start/finish line in meters
    x INT,                                       -- X coordinate for SVG mapping
    y INT,                                       -- Y coordinate for SVG mapping  
    z INT,                                       -- Z coordinate (elevation) for 3D
    
    -- Turn identification
    name TEXT,                                   -- Official turn name (e.g., "La Source", "Eau Rouge", "Maggotts")
    local_name TEXT,                             -- Local/historical name if different
    
    -- Turn characteristics
    direction silver.turn_direction_enum,        -- Left, right, or straight (chicane exit)
    angle_degrees INT,                           -- Approximate turn angle (90 = right angle, 180 = hairpin)
    radius_m NUMERIC(6,1),                       -- Corner radius in meters (smaller = tighter)
    camber_degrees NUMERIC(4,1),                 -- Track camber through turn (+ve = banked, -ve = off-camber)
    
    -- Speed data
    entry_speed_kph INT,                         -- Typical entry speed
    apex_speed_kph INT,                          -- Typical minimum/apex speed  
    exit_speed_kph INT,                          -- Typical exit speed
    turn_character silver.turn_character_enum,   -- How the turn is taken (flat out, lift, braking, etc.)
    
    -- Track features
    sector INT CHECK (sector IN (1, 2, 3)),      -- Which sector the turn is in
    drs_zone_after BOOLEAN DEFAULT FALSE,        -- Does this turn lead into a DRS zone?
    drs_detection_point BOOLEAN DEFAULT FALSE,   -- Is DRS detection at this turn?
    
    -- Overtaking & racing
    overtaking_rating silver.overtaking_rating_enum,  -- Overtaking opportunity rating
    is_key_overtaking_spot BOOLEAN DEFAULT FALSE,     -- Famous overtaking location
    
    -- Turn grouping (for chicanes/complexes)
    is_complex_part BOOLEAN DEFAULT FALSE,       -- Part of a multi-turn complex?
    complex_name TEXT,                           -- Name of the complex (e.g., "Maggotts-Becketts")
    complex_position INT,                        -- Position within complex (1, 2, 3...)
    
    -- Safety
    runoff_type TEXT,                            -- 'gravel', 'asphalt', 'grass', 'barrier'
    has_tecpro BOOLEAN,                          -- TecPro barrier present?
    
    -- Metadata
    elevation_change_m NUMERIC(5,1),             -- Elevation change through turn
    notes TEXT,                                  -- Additional notes/description
    
    -- Constraints
    UNIQUE (circuit_id, turn_number)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_turns_circuit_id 
    ON silver.turns(circuit_id);
CREATE INDEX IF NOT EXISTS idx_turns_circuit_turn 
    ON silver.turns(circuit_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_turns_overtaking 
    ON silver.turns(is_key_overtaking_spot) WHERE is_key_overtaking_spot = TRUE;
CREATE INDEX IF NOT EXISTS idx_turns_sector 
    ON silver.turns(circuit_id, sector);

-- Add comment for documentation
COMMENT ON TABLE silver.turns IS 'Circuit turn/corner reference data for track mapping, telemetry overlay, and turn-by-turn analysis';
COMMENT ON COLUMN silver.turns.track_distance_m IS 'Distance from start/finish line in meters';
COMMENT ON COLUMN silver.turns.x IS 'X coordinate for SVG track map overlay';
COMMENT ON COLUMN silver.turns.y IS 'Y coordinate for SVG track map overlay';
COMMENT ON COLUMN silver.turns.z IS 'Z coordinate (elevation) for 3D visualization';
COMMENT ON COLUMN silver.turns.turn_character IS 'How the turn is typically taken: flat_out, lift, braking, heavy_braking, or hairpin';
COMMENT ON COLUMN silver.turns.complex_name IS 'For multi-turn sequences like Maggotts-Becketts or Esses';




