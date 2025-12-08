-- Create a helper lookup for sector segment values → meaning/color

CREATE TABLE IF NOT EXISTS silver.segment_meaning (
    segment_value INT PRIMARY KEY,
    color_label TEXT,
    meaning TEXT,
    notes TEXT
);

-- Seed known mappings (idempotent)
INSERT INTO silver.segment_meaning (segment_value, color_label, meaning, notes) VALUES
    (0,    'not available',  'no segment timing available', 'Segments are not available during races'),
    (2048, 'yellow sector',  'yellow sector', NULL),
    (2049, 'green sector',   'green sector', NULL),
    (2050, NULL,             NULL, NULL),
    (2051, 'purple sector',  'purple sector (fastest)', NULL),
    (2052, NULL,             NULL, NULL),
    (2064, 'pitlane',        'pitlane', NULL),
    (2068, NULL,             NULL, NULL)
ON CONFLICT (segment_value) DO UPDATE
SET 
    color_label = EXCLUDED.color_label,
    meaning = EXCLUDED.meaning,
    notes = EXCLUDED.notes;


