-- Gold layer: Segment Meaning Dimension
-- Dimension view for segment value mappings, used for frontend color coding

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.dim_segment_meaning AS
SELECT
    segment_value,
    color_label,
    meaning,
    notes
FROM silver.segment_meaning
ORDER BY segment_value;

-- Create index on segment_meaning dimension for performance
CREATE INDEX IF NOT EXISTS idx_dim_segment_meaning_segment_value 
    ON gold.dim_segment_meaning(segment_value);

