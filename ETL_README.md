# Pitwall ETL Pipeline

This document describes the data ingestion and transformation pipeline for the Pitwall F1 database.

## Quick Start: One-Command Update

The easiest way to update the database is with the unified script:

```bash
# Full pipeline (recommended for most updates)
python3 update_database.py

# Skip high-volume GPS/telemetry data (faster)
python3 update_database.py --skip-high-volume

# Only refresh gold materialized views (fastest)
python3 update_database.py --gold-only

# Output results as JSON
python3 update_database.py --json
```

**From the Frontend:**
Click the database icon in the header → Database Admin page to trigger updates via the UI.

---

## Architecture Overview

```
OpenF1 API → Bronze (Raw) → Silver (Cleaned) → Gold (Aggregated)
```

- **Bronze Layer**: Raw data ingestion from OpenF1 API (append-only, TEXT columns)
- **Silver Layer**: Cleaned, typed, and normalized data with referential integrity  
- **Gold Layer**: Aggregated materialized views for analytics and API

---

## Table Dependencies

### Bronze Layer (No Dependencies)
Bronze tables are raw ingestion targets with no foreign keys:
- `bronze.meetings_raw`
- `bronze.sessions_raw`
- `bronze.drivers_raw`
- `bronze.laps_raw`
- `bronze.results_raw`
- `bronze.race_control_raw`
- `bronze.starting_grid_raw`
- `bronze.pit_stops_raw`
- `bronze.stints_raw`
- `bronze.weather_raw`
- `bronze.overtakes_raw`
- `bronze.intervals_raw`
- `bronze.position_raw`
- `bronze.car_telemetry_raw` (high-volume)
- `bronze.car_gps_raw` (high-volume)

### Silver Layer Dependencies

```
silver.countries (reference data, pre-seeded)
       ↓
silver.circuits → silver.meetings → silver.sessions
                                          ↓
       silver.teams → silver.team_branding
            ↓
       silver.drivers → silver.driver_numbers_by_season
            ↓
       silver.driver_teams_by_session
                    ↓
    ┌───────────────┴───────────────┐
    ↓               ↓               ↓
silver.laps   silver.results   silver.race_control
    ↓
silver.stints (depends on laps for lap_start_id/lap_end_id)
silver.pit_stops (depends on laps for lap_id)
silver.weather
silver.overtakes
silver.intervals
silver.position
silver.car_telemetry (high-volume)
silver.car_gps (high-volume)
```

---

## Script Execution Order

### Phase 1: Bronze Ingestion (from OpenF1 API)

Run in this order:

```bash
# 1. Foundation tables (must run first)
python3 pitwall_ingest/ingest_meetings.py
python3 pitwall_ingest/ingest_sessions.py
python3 pitwall_ingest/ingest_drivers.py

# 2. Session-dependent tables (can run in parallel after above)
python3 pitwall_ingest/ingest_laps.py
python3 pitwall_ingest/ingest_results.py
python3 pitwall_ingest/ingest_race_control.py
python3 pitwall_ingest/ingest_starting_grid.py
python3 pitwall_ingest/ingest_pit_stops.py
python3 pitwall_ingest/ingest_stints.py
python3 pitwall_ingest/ingest_weather.py
python3 pitwall_ingest/ingest_overtakes.py
python3 pitwall_ingest/ingest_intervals.py
python3 pitwall_ingest/ingest_position.py

# 3. High-volume tables (run last, can use background runner)
# See Phase 4 below
```

### Phase 2: Silver Upserts (Bronze → Silver)

Run in this order (dependencies matter):

```bash
# 1. Reference/Foundation tables
python3 pitwall_silver/upsert_circuits.py    # Depends on: countries (pre-seeded)
python3 pitwall_silver/upsert_meetings.py    # Depends on: circuits
python3 pitwall_silver/upsert_sessions.py    # Depends on: meetings, circuits

# 2. Team and Driver tables
python3 pitwall_silver/upsert_drivers.py                    # No silver dependencies
python3 pitwall_silver/upsert_driver_numbers_by_season.py   # Depends on: drivers
python3 pitwall_silver/upsert_driver_teams_by_session.py    # Depends on: drivers, sessions, teams
python3 pitwall_silver/upsert_team_branding.py              # Depends on: teams

# 3. Session data tables
python3 pitwall_silver/upsert_laps.py         # Depends on: sessions, drivers
python3 pitwall_silver/upsert_results.py      # Depends on: sessions, drivers
python3 pitwall_silver/upsert_race_control.py # Depends on: sessions, drivers

# 4. Tables that depend on laps
python3 pitwall_silver/upsert_stints.py       # Depends on: sessions, drivers, laps
python3 pitwall_silver/upsert_pit_stops.py    # Depends on: sessions, drivers, laps

# 5. Other session data (can run in parallel)
python3 pitwall_silver/upsert_weather.py      # Depends on: sessions
python3 pitwall_silver/upsert_overtakes.py    # Depends on: sessions, drivers
python3 pitwall_silver/upsert_intervals.py    # Depends on: sessions, drivers
python3 pitwall_silver/upsert_position.py     # Depends on: sessions, drivers
python3 pitwall_silver/upsert_points_awarding.py  # Depends on: sessions
```

### Phase 3: Post-Processing

```bash
# Update lap validity flags (after pit_stops)
python3 pitwall_silver/backfill_lap_validity.py
```

### Phase 4: High-Volume Upserts (Background)

These scripts process millions of rows and should run in the background:

```bash
# Run with caffeinate to prevent system sleep on macOS
python3 run_high_volume_upserts.py
```

This runs:
- `pitwall_silver/upsert_car_telemetry.py`
- `pitwall_silver/upsert_car_gps.py`

Monitor progress:
```bash
tail -f logs/upsert_car_*.log
ps aux | grep -E 'upsert_car_(telemetry|gps)'
```

### Phase 5: Gold Layer Refresh

After silver upserts complete, refresh materialized views:

```sql
-- Run these in order (or use refresh_standings_views.py)
REFRESH MATERIALIZED VIEW gold.driver_standings_progression;
REFRESH MATERIALIZED VIEW gold.constructor_standings_progression;
REFRESH MATERIALIZED VIEW gold.driver_session_results;
REFRESH MATERIALIZED VIEW gold.session_classification;
REFRESH MATERIALIZED VIEW gold.session_summary;
REFRESH MATERIALIZED VIEW gold.lap_times;
REFRESH MATERIALIZED VIEW gold.lap_intervals;
REFRESH MATERIALIZED VIEW gold.dim_drivers;
REFRESH MATERIALIZED VIEW gold.dim_teams;
REFRESH MATERIALIZED VIEW gold.dim_meetings;
REFRESH MATERIALIZED VIEW gold.dim_circuits;
REFRESH MATERIALIZED VIEW gold.circuit_overtake_stats;
```

Or use:
```bash
python3 pitwall_silver/refresh_standings_views.py
```

---

## Quick Reference: Full Pipeline

```bash
# === BRONZE INGESTION ===
echo "=== Phase 1: Bronze Ingestion ==="
python3 pitwall_ingest/ingest_meetings.py
python3 pitwall_ingest/ingest_sessions.py
python3 pitwall_ingest/ingest_drivers.py
python3 pitwall_ingest/ingest_laps.py
python3 pitwall_ingest/ingest_results.py
python3 pitwall_ingest/ingest_race_control.py
python3 pitwall_ingest/ingest_starting_grid.py
python3 pitwall_ingest/ingest_pit_stops.py
python3 pitwall_ingest/ingest_stints.py
python3 pitwall_ingest/ingest_weather.py
python3 pitwall_ingest/ingest_overtakes.py
python3 pitwall_ingest/ingest_intervals.py
python3 pitwall_ingest/ingest_position.py

# === SILVER UPSERTS ===
echo "=== Phase 2: Silver Upserts ==="
python3 pitwall_silver/upsert_circuits.py
python3 pitwall_silver/upsert_meetings.py
python3 pitwall_silver/upsert_sessions.py
python3 pitwall_silver/upsert_drivers.py
python3 pitwall_silver/upsert_driver_numbers_by_season.py
python3 pitwall_silver/upsert_driver_teams_by_session.py
python3 pitwall_silver/upsert_team_branding.py
python3 pitwall_silver/upsert_laps.py
python3 pitwall_silver/upsert_results.py
python3 pitwall_silver/upsert_race_control.py
python3 pitwall_silver/upsert_stints.py
python3 pitwall_silver/upsert_pit_stops.py
python3 pitwall_silver/upsert_weather.py
python3 pitwall_silver/upsert_overtakes.py
python3 pitwall_silver/upsert_intervals.py
python3 pitwall_silver/upsert_position.py
python3 pitwall_silver/upsert_points_awarding.py

# === POST-PROCESSING ===
echo "=== Phase 3: Post-Processing ==="
python3 pitwall_silver/backfill_lap_validity.py

# === GOLD REFRESH ===
echo "=== Phase 5: Gold Refresh ==="
python3 pitwall_silver/refresh_standings_views.py

# === HIGH-VOLUME (Background) ===
echo "=== Phase 4: High-Volume Upserts (Background) ==="
python3 run_high_volume_upserts.py
```

---

## Incremental Updates

All ingest scripts are designed for incremental updates:
- They check for existing data before fetching
- Only new meeting/session keys are processed
- Silver upserts use ON CONFLICT DO UPDATE patterns

To update with latest data, simply re-run the pipeline - it will only process new data.

---

## Monitoring

### Check Bronze Counts
```sql
SELECT 'meetings_raw' as table_name, COUNT(*) FROM bronze.meetings_raw
UNION ALL SELECT 'sessions_raw', COUNT(*) FROM bronze.sessions_raw
UNION ALL SELECT 'drivers_raw', COUNT(*) FROM bronze.drivers_raw
UNION ALL SELECT 'laps_raw', COUNT(*) FROM bronze.laps_raw
ORDER BY table_name;
```

### Check Silver Counts
```sql
SELECT 'meetings' as table_name, COUNT(*) FROM silver.meetings
UNION ALL SELECT 'sessions', COUNT(*) FROM silver.sessions
UNION ALL SELECT 'drivers', COUNT(*) FROM silver.drivers
UNION ALL SELECT 'laps', COUNT(*) FROM silver.laps
ORDER BY table_name;
```

### Check Latest Data
```sql
SELECT MAX(season) as latest_season, 
       MAX(date_start) as latest_meeting 
FROM silver.meetings;

SELECT MAX(start_time) as latest_session 
FROM silver.sessions;
```

---

## API Endpoints for Database Updates

The API provides endpoints to trigger and monitor database updates:

### GET /api/database/status
Returns current database statistics and update status.

### POST /api/database/update
Triggers a full database update (bronze → silver → gold).
- Query param: `skip_high_volume=true` (default) to skip GPS/telemetry

### POST /api/database/refresh-gold
Quickly refresh only the gold materialized views.

---

## Files

| File | Purpose |
|------|---------|
| `update_database.py` | Unified ETL orchestrator |
| `pitwall_ingest/*.py` | Bronze layer ingestion scripts |
| `pitwall_silver/*.py` | Silver layer upsert scripts |
| `run_high_volume_upserts.py` | Background runner for GPS/telemetry |
| `api/main.py` | FastAPI backend with database endpoints |
| `frontend/src/components/DatabaseAdmin.tsx` | UI for database updates |

