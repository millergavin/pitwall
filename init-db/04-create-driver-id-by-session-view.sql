-- Create driver_id_by_session view
-- This view joins driver data per session and is used to resolve driver_id
-- for tables where source data only includes (driver_number, openf1_session_key)

CREATE OR REPLACE VIEW silver.driver_id_by_session AS
SELECT 
    s.openf1_session_key,
    s.session_id,
    s.meeting_id,
    m.season,
    dns.driver_number,
    dns.driver_id,
    d.name_acronym,
    dtbs.team_id,
    tb.team_name,
    tb.display_name,
    tb.color_hex,
    tb.logo_url,
    tb.car_image_url,
    d.full_name AS driver_name
FROM silver.sessions s
INNER JOIN silver.meetings m 
    ON s.meeting_id = m.meeting_id
INNER JOIN silver.driver_numbers_by_season dns 
    ON m.season = dns.season
LEFT JOIN silver.drivers d 
    ON dns.driver_id = d.driver_id
LEFT JOIN silver.driver_teams_by_session dtbs 
    ON s.session_id = dtbs.session_id 
    AND dns.driver_id = dtbs.driver_id
LEFT JOIN silver.team_branding tb 
    ON dtbs.team_id = tb.team_id 
    AND m.season = tb.season;


