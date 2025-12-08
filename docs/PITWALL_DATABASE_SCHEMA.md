# Pitwall Database Schema Documentation

**Generated:** December 2, 2025  
**Database:** pitwall  
**Version:** 1.0

---

## Table of Contents
1. [Overview](#overview)
2. [Database Architecture](#database-architecture)
3. [Bronze Layer](#bronze-layer)
4. [Silver Layer](#silver-layer)
5. [Gold Layer](#gold-layer)
6. [Enumerated Types](#enumerated-types)
7. [Entity Relationship Diagram](#entity-relationship-diagram)
8. [Indexes](#indexes)

---

## Overview

The Pitwall database is a PostgreSQL database designed to ingest, process, and serve Formula 1 telemetry and session data. It follows a **medallion architecture** with three layers:

- **Bronze**: Raw data ingestion from OpenF1 API
- **Silver**: Cleaned, validated, and enriched data with proper typing
- **Gold**: Aggregated views and analytics-ready datasets

The database is owned by the `pitwall` role with a default search path of: `"$user", bronze, silver, gold, public`.

---

## Database Architecture

### Schemas

```
pitwall/
├── bronze (raw data)
├── silver (cleaned & normalized data)
└── gold (analytics views)
```

### Data Flow

```
OpenF1 API → Bronze Tables → Silver Tables → Gold Materialized Views → API/Frontend
```

---

## Bronze Layer

**Purpose**: Raw data ingestion from OpenF1 API. All columns are TEXT (nullable) except `ingested_at` which is TIMESTAMPTZ (NOT NULL).

### Tables

#### 1. `bronze.meetings_raw`
Stores raw meeting/Grand Prix data.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_circuit_key` | TEXT | OpenF1 circuit identifier |
| `circuit_short_name` | TEXT | Short name of circuit |
| `country_code` | TEXT | Country code |
| `location` | TEXT | Location/city name |
| `gmt_offset` | TEXT | GMT offset |
| `country_name` | TEXT | Country name |
| `country_key` | TEXT | Country key |
| `meeting_name` | TEXT | Meeting name |
| `season` | TEXT | Season year |
| `meeting_official_name` | TEXT | Official meeting name |
| `date_start` | TEXT | Start date (text) |
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 2. `bronze.sessions_raw`
Stores raw session data (Practice, Qualifying, Sprint, Race).

| Column | Type | Description |
|--------|------|-------------|
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `date_start` | TEXT | Session start date/time |
| `date_end` | TEXT | Session end date/time |
| `session_name` | TEXT | Session name |
| `openf1_circuit_key` | TEXT | OpenF1 circuit identifier |
| `circuit_short_name` | TEXT | Circuit short name |
| `country_code` | TEXT | Country code |
| `country_key` | TEXT | Country key |
| `country_name` | TEXT | Country name |
| `gmt_offset` | TEXT | GMT offset |
| `location` | TEXT | Location |
| `session_type` | TEXT | Session type |
| `year` | TEXT | Year |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 3. `bronze.results_raw`
Stores raw session results.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `driver_number` | TEXT | Driver number |
| `position` | TEXT | Final position |
| `gap_to_leader_s` | TEXT | Gap to leader in seconds |
| `duration_s` | TEXT | Race/session duration |
| `laps_completed` | TEXT | Number of laps completed |
| `dnf` | TEXT | Did Not Finish flag |
| `dns` | TEXT | Did Not Start flag |
| `dsq` | TEXT | Disqualified flag |
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 4. `bronze.laps_raw`
Stores raw lap-by-lap data.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `driver_number` | TEXT | Driver number |
| `lap_number` | TEXT | Lap number |
| `date_start` | TEXT | Lap start time |
| `lap_duration_s` | TEXT | Total lap time |
| `duration_s1_s` | TEXT | Sector 1 time |
| `duration_s2_s` | TEXT | Sector 2 time |
| `duration_s3_s` | TEXT | Sector 3 time |
| `i1_speed_kph` | TEXT | Speed at intermediate 1 |
| `i2_speed_kph` | TEXT | Speed at intermediate 2 |
| `st_speed_kph` | TEXT | Speed trap speed |
| `is_pit_out_lap` | TEXT | Pit out lap flag |
| `s1_segments` | TEXT | Sector 1 segment data |
| `s2_segments` | TEXT | Sector 2 segment data |
| `s3_segments` | TEXT | Sector 3 segment data |
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 5. `bronze.drivers_raw`
Stores raw driver data.

| Column | Type | Description |
|--------|------|-------------|
| `broadcast_name` | TEXT | Broadcast name |
| `team_name` | TEXT | Team name |
| `team_color_hex` | TEXT | Team color (hex) |
| `first_name` | TEXT | First name |
| `last_name` | TEXT | Last name |
| `full_name` | TEXT | Full name |
| `name_acronym` | TEXT | 3-letter acronym |
| `country_code` | TEXT | Country code |
| `headshot_url` | TEXT | Driver headshot URL |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `driver_number` | TEXT | Driver number |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 6. `bronze.race_control_raw`
Stores raw race control messages.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `category` | TEXT | Message category |
| `date` | TEXT | Message timestamp |
| `driver_number` | TEXT | Driver number |
| `flag` | TEXT | Flag type (RED, YELLOW, etc.) |
| `lap_number` | TEXT | Lap number |
| `message` | TEXT | Message text |
| `scope` | TEXT | Message scope |
| `sector` | TEXT | Sector |
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 7. `bronze.starting_grid_raw`
Stores raw starting grid positions.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `driver_number` | TEXT | Driver number |
| `position` | TEXT | Grid position |
| `lap_duration_s` | TEXT | Qualifying lap time |
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 8. `bronze.weather_raw`
Stores raw weather data.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `date` | TEXT | Timestamp |
| `air_temp_c` | TEXT | Air temperature (°C) |
| `humidity` | TEXT | Humidity (%) |
| `pressure` | TEXT | Atmospheric pressure |
| `rainfall` | TEXT | Rainfall indicator |
| `track_temp_c` | TEXT | Track temperature (°C) |
| `wind_direction` | TEXT | Wind direction (degrees) |
| `wind_speed_mps` | TEXT | Wind speed (m/s) |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 9. `bronze.car_telemetry_raw`
Stores raw car telemetry (throttle, brake, RPM, etc.).

| Column | Type | Description |
|--------|------|-------------|
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `date` | TEXT | Timestamp |
| `driver_number` | TEXT | Driver number |
| `brake` | TEXT | Brake pressure (%) |
| `drs` | TEXT | DRS status |
| `n_gear` | TEXT | Current gear |
| `rpm` | TEXT | Engine RPM |
| `speed_kph` | TEXT | Speed (km/h) |
| `throttle` | TEXT | Throttle position (%) |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 10. `bronze.car_gps_raw`
Stores raw GPS coordinates.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `date` | TEXT | Timestamp |
| `driver_number` | TEXT | Driver number |
| `x` | TEXT | X coordinate |
| `y` | TEXT | Y coordinate |
| `z` | TEXT | Z coordinate |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 11. `bronze.overtakes_raw`
Stores raw overtake events.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `date` | TEXT | Timestamp |
| `overtaken_driver_number` | TEXT | Overtaken driver |
| `overtaking_driver_number` | TEXT | Overtaking driver |
| `position` | TEXT | Position at overtake |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 12. `bronze.intervals_raw`
Stores raw timing intervals.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `driver_number` | TEXT | Driver number |
| `date` | TEXT | Timestamp |
| `gap_to_leader_s` | TEXT | Gap to leader |
| `interval_s` | TEXT | Interval to car ahead |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 13. `bronze.position_raw`
Stores raw position data.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `driver_number` | TEXT | Driver number |
| `date` | TEXT | Timestamp |
| `position` | TEXT | Current position |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 14. `bronze.stints_raw`
Stores raw stint/tyre strategy data.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `driver_number` | TEXT | Driver number |
| `stint_number` | TEXT | Stint number |
| `lap_start` | TEXT | Start lap |
| `lap_end` | TEXT | End lap |
| `compound` | TEXT | Tyre compound |
| `tyre_age_at_start` | TEXT | Tyre age at start |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

#### 15. `bronze.pit_stops_raw`
Stores raw pit stop data.

| Column | Type | Description |
|--------|------|-------------|
| `openf1_meeting_key` | TEXT | OpenF1 meeting identifier |
| `openf1_session_key` | TEXT | OpenF1 session identifier |
| `driver_number` | TEXT | Driver number |
| `date` | TEXT | Timestamp |
| `lap_number` | TEXT | Lap number |
| `pit_duration_s` | TEXT | Pit stop duration |
| `ingested_at` | TIMESTAMPTZ | Ingestion timestamp |

---

## Silver Layer

**Purpose**: Cleaned, validated, and enriched data with proper typing and referential integrity.

### Reference Data Tables

#### 1. `silver.countries`
Master table for countries.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `country_code` | CHAR(3) | PRIMARY KEY, NOT NULL | ISO 3166-1 alpha-3 code |
| `country_name` | TEXT | NOT NULL | Country name |
| `alpha2` | CHAR(2) | | ISO 3166-1 alpha-2 code |
| `numeric_code` | INT | | ISO numeric code |
| `lat_avg` | NUMERIC(9,6) | NOT NULL | Average latitude |
| `lon_avg` | NUMERIC(9,6) | NOT NULL | Average longitude |
| `demonym` | TEXT | | Demonym (e.g., "British") |
| `emoji_flag` | TEXT | | Emoji flag representation |
| `flag_url` | TEXT | | Flag image URL |

#### 2. `silver.country_code_alias`
Aliases for country codes (e.g., mapping variations).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `alias` | TEXT | PRIMARY KEY, NOT NULL | Alias |
| `country_code` | CHAR(3) | FK → countries, NOT NULL | Target country code |

#### 3. `silver.circuits`
Master table for F1 circuits.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `circuit_id` | TEXT | PRIMARY KEY, NOT NULL | Circuit identifier |
| `openf1_circuit_key` | TEXT | NOT NULL | OpenF1 key |
| `circuit_short_name` | TEXT | NOT NULL | Short name |
| `country_code` | CHAR(3) | FK → countries, NOT NULL | Country |
| `location` | TEXT | | City/location |
| `lat` | NUMERIC(9,6) | | Latitude |
| `lon` | NUMERIC(9,6) | | Longitude |
| `timezone_tzid` | TEXT | | Timezone (IANA) |
| `circuit_name` | TEXT | | Full circuit name |
| `lap_length_km` | NUMERIC(6,3) | | Lap length (km) |
| `fastest_lap_time_ms` | INT | | Circuit record lap time (ms) |
| `fastest_lap_driver_id` | TEXT | | Driver holding record |
| `fastest_lap_year` | INT | | Year of record |
| `circuit_svg` | TEXT | | SVG track map |
| `race_laps` | INT | | Number of laps in race |
| `sprint_laps` | INT | | Number of laps in sprint |

### Event Tables

#### 4. `silver.meetings`
F1 Grand Prix events/weekends. Supports both historical (ingested) and future (scheduled) meetings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `meeting_id` | TEXT | PRIMARY KEY, NOT NULL | Meeting identifier |
| `openf1_meeting_key` | TEXT | UNIQUE (where NOT NULL) | OpenF1 key (NULL for future meetings until data is ingested) |
| `circuit_id` | TEXT | FK → circuits, NOT NULL | Circuit |
| `meeting_name` | TEXT | NOT NULL | Meeting name |
| `season` | INT | NOT NULL | Season year |
| `meeting_official_name` | TEXT | | Official name |
| `date_start` | TIMESTAMPTZ | NOT NULL | Start date/time |
| `date_end` | TIMESTAMPTZ | | End date/time |
| `round_number` | INT | | Round number in season |

**Note:** `openf1_meeting_key` is nullable to allow future/scheduled meetings to be pre-populated before OpenF1 has data. When meeting data is ingested and upserted, the key is filled in automatically via matching `meeting_id`.

#### 5. `silver.sessions`
Individual sessions (Practice, Qualifying, Sprint, Race).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `session_id` | TEXT | PRIMARY KEY, NOT NULL | Session identifier |
| `meeting_id` | TEXT | FK → meetings, NOT NULL | Parent meeting |
| `openf1_session_key` | TEXT | NOT NULL | OpenF1 key |
| `start_time` | TIMESTAMPTZ | NOT NULL | Start time |
| `end_time` | TIMESTAMPTZ | NOT NULL | End time |
| `session_name` | TEXT | NOT NULL | Session name |
| `session_type` | session_type_enum | | Type enum |
| `scheduled_laps` | INT | | Scheduled laps |
| `completed_laps` | INT | | Completed laps |
| `points_awarding` | points_awarding_enum | NOT NULL, DEFAULT 'none' | Points type |
| `duration_min` | INT | | Duration (minutes) |

### Team & Driver Tables

#### 6. `silver.teams`
Master table for teams/constructors.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `team_id` | TEXT | PRIMARY KEY, NOT NULL | Team identifier |

#### 7. `silver.team_branding`
Team branding by season.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `team_id` | TEXT | FK → teams, PK | Team identifier |
| `team_name` | TEXT | PK, NOT NULL | Team name |
| `season` | INT | PK, NOT NULL | Season |
| `color_hex` | TEXT | NOT NULL | Primary color |
| `display_name` | TEXT | | Display name |
| `logo_url` | TEXT | | Logo URL |

#### 8. `silver.team_alias`
Team name aliases.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `alias` | TEXT | PRIMARY KEY, NOT NULL | Alias |
| `team_id` | TEXT | FK → teams, NOT NULL | Target team |

#### 9. `silver.drivers`
Master table for drivers.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `driver_id` | TEXT | PRIMARY KEY, NOT NULL | Driver identifier |
| `first_name` | TEXT | NOT NULL | First name |
| `last_name` | TEXT | NOT NULL | Last name |
| `full_name` | TEXT | | Full name |
| `name_acronym` | CHAR(3) | NOT NULL | 3-letter acronym (e.g., VER) |
| `country_code` | CHAR(3) | FK → countries | Nationality |
| `headshot_url` | TEXT | | Headshot URL |
| `headshot_override` | TEXT | | Override headshot URL |
| `wikipedia_id` | TEXT | | Wikipedia page ID |
| `birthdate` | TIMESTAMPTZ | | Birth date |

#### 10. `silver.driver_numbers_by_season`
Driver racing numbers by season.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `driver_id` | TEXT | FK → drivers, PK | Driver |
| `season` | INT | PK, NOT NULL | Season |
| `driver_number` | INT | NOT NULL | Racing number |

#### 11. `silver.driver_teams_by_session`
Driver-team assignments per session.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `session_id` | TEXT | FK → sessions, PK | Session |
| `driver_id` | TEXT | FK → drivers, PK | Driver |
| `team_id` | TEXT | FK → teams, NOT NULL | Team |

#### 12. `silver.driver_alias`
Driver name aliases.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `alias` | TEXT | PRIMARY KEY, NOT NULL | Alias |
| `driver_id` | TEXT | FK → drivers, NOT NULL | Target driver |

### Session Data Tables

#### 13. `silver.laps`
Lap-by-lap timing data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `lap_id` | BIGINT | PRIMARY KEY, NOT NULL | Lap identifier |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `driver_id` | TEXT | FK → drivers, NOT NULL | Driver |
| `lap_number` | INT | NOT NULL | Lap number |
| `date_start` | TIMESTAMPTZ | NOT NULL | Lap start time |
| `lap_duration_ms` | INT | | Total lap time (ms) |
| `duration_s1_ms` | INT | | Sector 1 time (ms) |
| `duration_s2_ms` | INT | | Sector 2 time (ms) |
| `duration_s3_ms` | INT | | Sector 3 time (ms) |
| `i1_speed_kph` | NUMERIC(6,2) | | Intermediate 1 speed |
| `i2_speed_kph` | NUMERIC(6,2) | | Intermediate 2 speed |
| `st_speed_kph` | NUMERIC(6,2) | | Speed trap speed |
| `is_pit_out_lap` | BOOLEAN | | Pit out lap flag |
| `s1_segments` | JSONB | | Sector 1 segments |
| `s2_segments` | JSONB | | Sector 2 segments |
| `s3_segments` | JSONB | | Sector 3 segments |
| `is_pit_in_lap` | BOOLEAN | NOT NULL | Pit in lap flag |
| `is_valid` | BOOLEAN | NOT NULL | Valid lap flag |

#### 14. `silver.results`
Final session results.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `session_id` | TEXT | FK → sessions, PK | Session |
| `driver_id` | TEXT | FK → drivers, PK | Driver |
| `finish_position` | INT | | Final position |
| `gap_to_leader_ms` | INT | | Gap to leader (ms) |
| `duration_ms` | INT | | Session duration (ms) |
| `laps_completed` | INT | | Laps completed |
| `status` | status_enum | NOT NULL | Status (finished/dnf/dns/dsq/nc) |
| `points` | NUMERIC(5,2) | NOT NULL | Points awarded |
| `best_lap_ms` | INT | | Best lap time (ms) |
| `fastest_lap` | BOOLEAN | NOT NULL | Fastest lap bonus flag |
| `grid_position` | INT | | Starting grid position |
| `quali_lap_ms` | INT | | Qualifying lap time (ms) |

#### 15. `silver.race_control`
Race control messages and flags.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `message_id` | BIGINT | PRIMARY KEY, IDENTITY | Message ID |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `category` | TEXT | NOT NULL | Category |
| `date` | TIMESTAMPTZ | NOT NULL | Timestamp |
| `driver_id` | TEXT | FK → drivers | Driver (if applicable) |
| `flag` | TEXT | | Flag type |
| `lap_number` | INT | | Lap number |
| `message` | TEXT | | Message text |
| `scope` | TEXT | | Scope |
| `referenced_lap` | INT | | Referenced lap |
| `referenced_lap_id` | BIGINT | FK → laps | Referenced lap ID |

#### 16. `silver.stints`
Tyre stint data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `stint_id` | BIGINT | PRIMARY KEY, IDENTITY | Stint ID |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `driver_id` | TEXT | FK → drivers, NOT NULL | Driver |
| `lap_start` | INT | NOT NULL | Start lap number |
| `lap_start_id` | BIGINT | FK → laps, NOT NULL | Start lap ID |
| `lap_end` | INT | | End lap number |
| `lap_end_id` | BIGINT | FK → laps | End lap ID |
| `tyre_age_at_start` | INT | | Tyre age (laps) |
| `tyre_compound` | tyre_compound_enum | | Compound |
| `stint_number` | INT | | Stint number |

#### 17. `silver.pit_stops`
Pit stop events.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `pit_stop_id` | BIGINT | PRIMARY KEY, IDENTITY | Pit stop ID |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `driver_id` | TEXT | FK → drivers, NOT NULL | Driver |
| `date` | TIMESTAMPTZ | NOT NULL | Timestamp |
| `lap_number` | INT | NOT NULL | Lap number |
| `lap_id` | BIGINT | FK → laps, NOT NULL | Lap ID |
| `pit_duration_ms` | INT | | Duration (ms) |

### Telemetry Tables (High Volume)

#### 18. `silver.car_telemetry`
High-frequency car telemetry data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `car_telemetry_id` | BIGINT | PRIMARY KEY, IDENTITY | Telemetry ID |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `driver_id` | TEXT | FK → drivers, NOT NULL | Driver |
| `date` | TIMESTAMPTZ | NOT NULL | Timestamp |
| `drs` | INT | | DRS status |
| `n_gear` | INT | | Current gear |
| `rpm` | INT | | Engine RPM |
| `speed_kph` | INT | | Speed (km/h) |
| `throttle` | INT | | Throttle (%) |
| `brake` | INT | | Brake pressure (%) |

#### 19. `silver.car_gps`
High-frequency GPS position data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `car_gps_id` | BIGINT | PRIMARY KEY, IDENTITY | GPS ID |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `driver_id` | TEXT | FK → drivers, NOT NULL | Driver |
| `date` | TIMESTAMPTZ | NOT NULL | Timestamp |
| `x` | INT | | X coordinate |
| `y` | INT | | Y coordinate |
| `z` | INT | | Z coordinate |

#### 20. `silver.position`
Track position data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `position_id` | BIGINT | PRIMARY KEY, IDENTITY | Position ID |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `driver_id` | TEXT | FK → drivers, NOT NULL | Driver |
| `date` | TIMESTAMPTZ | NOT NULL | Timestamp |
| `position` | INT | | Current position |

#### 21. `silver.intervals`
Timing interval data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `interval_id` | BIGINT | PRIMARY KEY, IDENTITY | Interval ID |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `driver_id` | TEXT | FK → drivers, NOT NULL | Driver |
| `date` | TIMESTAMPTZ | NOT NULL | Timestamp |
| `gap_to_leader_ms` | INT | | Gap to leader (ms) |
| `interval_ms` | INT | | Interval to car ahead (ms) |

#### 22. `silver.overtakes`
Overtake events.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `overtake_id` | BIGINT | PRIMARY KEY, IDENTITY | Overtake ID |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `overtaken_driver_id` | TEXT | FK → drivers | Overtaken driver |
| `overtaking_driver_id` | TEXT | FK → drivers, NOT NULL | Overtaking driver |
| `position` | INT | NOT NULL | Position |
| `date` | TIMESTAMPTZ | NOT NULL | Timestamp |

### Weather & Points System

#### 23. `silver.weather`
Weather conditions during session.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `weather_id` | TEXT | PRIMARY KEY, NOT NULL | Weather ID |
| `session_id` | TEXT | FK → sessions, NOT NULL | Session |
| `date` | TIMESTAMPTZ | NOT NULL | Timestamp |
| `air_temp_c` | NUMERIC(6,3) | | Air temp (°C) |
| `track_temp_c` | NUMERIC(6,3) | | Track temp (°C) |
| `humidity` | INT | | Humidity (%) |
| `rainfall` | INT | | Rainfall |
| `pressure_mbar` | NUMERIC(7,3) | | Pressure (mbar) |
| `wind_direction` | INT | | Wind direction (°) |
| `wind_speed_mps` | NUMERIC(6,3) | | Wind speed (m/s) |

#### 24. `silver.completion_band`
Reference table for completion bands.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `completion_band` | completion_band_enum | PRIMARY KEY | Completion band |
| `range_represented` | TEXT | | Range description |
| `shorthand` | TEXT | | Short code |
| `notes` | TEXT | | Notes |

#### 25. `silver.points_system`
Points awarding system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `points_id` | TEXT | PRIMARY KEY, NOT NULL | Points system ID |
| `season` | INT | NOT NULL | Season |
| `race_type` | points_awarding_enum | NOT NULL | Race type |
| `completion_band` | completion_band_enum | NOT NULL | Completion band |
| `position` | INT | | Position |
| `bonus` | bonus_enum | | Bonus type |
| `points` | NUMERIC(4,1) | NOT NULL | Points awarded |

### Helper View

#### `silver.driver_id_by_session` (VIEW)
Joins driver data per session for easy resolution of driver_id from (driver_number, session_key).

| Column | Type | Description |
|--------|------|-------------|
| `openf1_session_key` | TEXT | OpenF1 session key |
| `session_id` | TEXT | Session ID |
| `meeting_id` | TEXT | Meeting ID |
| `season` | INT | Season |
| `driver_number` | INT | Driver number |
| `driver_id` | TEXT | Driver ID |
| `name_acronym` | CHAR(3) | Driver acronym |
| `team_id` | TEXT | Team ID |
| `team_name` | TEXT | Team name |
| `display_name` | TEXT | Display name |
| `color_hex` | TEXT | Team color |
| `logo_url` | TEXT | Logo URL |
| `car_image_url` | TEXT | Car image URL |
| `driver_name` | TEXT | Driver full name |

---

## Gold Layer

**Purpose**: Aggregated, analytics-ready materialized views for the frontend and API.

### Standings & Championship Views

#### 1. `gold.driver_standings_progression`
Season-long driver championship progression.

**Purpose**: Plot how driver standings evolve after each sprint/race.

| Column | Type | Description |
|--------|------|-------------|
| `season` | INT | Season |
| `round_number` | INT | Round number |
| `session_id` | TEXT | Session ID |
| `session_type` | session_type_enum | Session type |
| `meeting_name` | TEXT | Meeting official name |
| `meeting_short_name` | TEXT | Meeting short name |
| `country_code` | CHAR(3) | Country code |
| `country_name` | TEXT | Country name |
| `emoji_flag` | TEXT | Flag emoji |
| `flag_url` | TEXT | Flag URL |
| `driver_id` | TEXT | Driver ID |
| `driver_number` | INT | Driver number |
| `driver_name` | TEXT | Driver name |
| `name_acronym` | CHAR(3) | Driver acronym |
| `driver_headshot_url` | TEXT | Headshot URL |
| `driver_headshot_override` | TEXT | Headshot override URL |
| `team_id` | TEXT | Team ID |
| `team_name` | TEXT | Team name |
| `display_name` | TEXT | Display name |
| `color_hex` | TEXT | Team color |
| `team_logo_url` | TEXT | Team logo URL |
| `finish_position` | INT | Finish position |
| `fastest_lap` | BOOLEAN | Fastest lap bonus |
| `session_points` | NUMERIC(5,2) | Points from session |
| `cumulative_points` | NUMERIC | Cumulative points |

**Indexes:**
- `idx_driver_standings_progression_season_driver` on (season, driver_id)
- `idx_driver_standings_progression_session` on (session_id)

#### 2. `gold.constructor_standings_progression`
Season-long constructor championship progression.

**Purpose**: Track constructors' championship evolution.

| Column | Type | Description |
|--------|------|-------------|
| `season` | INT | Season |
| `round_number` | INT | Round number |
| `session_id` | TEXT | Session ID |
| `session_type` | session_type_enum | Session type |
| `meeting_name` | TEXT | Meeting official name |
| `meeting_short_name` | TEXT | Meeting short name |
| `country_code` | CHAR(3) | Country code |
| `country_name` | TEXT | Country name |
| `emoji_flag` | TEXT | Flag emoji |
| `flag_url` | TEXT | Flag URL |
| `team_id` | TEXT | Team ID |
| `team_name` | TEXT | Team name |
| `display_name` | TEXT | Display name |
| `color_hex` | TEXT | Team color |
| `team_logo_url` | TEXT | Team logo URL |
| `session_points` | NUMERIC | Points from session |
| `cumulative_points` | NUMERIC | Cumulative points |

**Indexes:**
- `idx_constructor_standings_progression_season_team` on (season, team_id)
- `idx_constructor_standings_progression_session` on (session_id)

### Session Results Views

#### 3. `gold.driver_session_results`
Main fact table for per-session driver performance.

**Purpose**: Power charts and tables across all session types.

| Column | Type | Description |
|--------|------|-------------|
| `season` | INT | Season |
| `round_number` | INT | Round number |
| `meeting_official_name` | TEXT | Meeting name |
| `circuit_name` | TEXT | Circuit name |
| `timezone_tzid` | TEXT | Timezone |
| `session_id` | TEXT | Session ID |
| `session_type` | session_type_enum | Session type |
| `start_time` | TIMESTAMPTZ | Start time |
| `end_time` | TIMESTAMPTZ | End time |
| `driver_id` | TEXT | Driver ID |
| `driver_number` | INT | Driver number |
| `driver_name` | TEXT | Driver name |
| `name_acronym` | CHAR(3) | Driver acronym |
| `team_id` | TEXT | Team ID |
| `team_name` | TEXT | Team name |
| `display_name` | TEXT | Display name |
| `color_hex` | TEXT | Team color |
| `grid_position` | INT | Grid position |
| `finish_position` | INT | Finish position |
| `status` | status_enum | Status |
| `laps_completed` | INT | Laps completed |
| `duration_ms` | INT | Duration (ms) |
| `gap_to_leader_ms` | INT | Gap to leader (ms) |
| `points` | NUMERIC(5,2) | Points |
| `fastest_lap` | BOOLEAN | Fastest lap |
| `best_lap_ms` | INT | Best lap time (ms) |
| `quali_lap_ms` | INT | Qualifying lap (ms) |

**Indexes:**
- `idx_driver_session_results_session_driver` on (session_id, driver_id)
- `idx_driver_session_results_season` on (season)
- `idx_driver_session_results_session_type` on (session_type)

#### 4. `gold.session_classification`
Classification for race/sprint/quali sessions.

**Purpose**: Timing sheet-style views.

| Column | Type | Description |
|--------|------|-------------|
| `season` | INT | Season |
| `round_number` | INT | Round number |
| `meeting_official_name` | TEXT | Meeting name |
| `circuit_id` | TEXT | Circuit ID |
| `circuit_name` | TEXT | Circuit name |
| `circuit_short_name` | TEXT | Circuit short name |
| `session_type` | session_type_enum | Session type |
| `session_id` | TEXT | Session ID |
| `driver_id` | TEXT | Driver ID |
| `driver_number` | INT | Driver number |
| `driver_name` | TEXT | Driver name |
| `name_acronym` | CHAR(3) | Driver acronym |
| `team_id` | TEXT | Team ID |
| `team_name` | TEXT | Team name |
| `display_name` | TEXT | Display name |
| `color_hex` | TEXT | Team color |
| `grid_position` | INT | Grid position |
| `finish_position` | INT | Finish position |
| `status` | status_enum | Status |
| `laps_completed` | INT | Laps completed |
| `duration_ms` | INT | Duration (ms) |
| `gap_to_leader_ms` | INT | Gap to leader (ms) |
| `best_lap_ms` | INT | Best lap (ms) |
| `fastest_lap` | BOOLEAN | Fastest lap |
| `points` | NUMERIC(5,2) | Points |

**Indexes:**
- `idx_session_classification_session_driver` on (session_id, driver_id)
- `idx_session_classification_season` on (season)
- `idx_session_classification_session_type` on (session_type)

#### 5. `gold.session_summary`
Session-level aggregated metadata.

**Purpose**: Single-row summary per session with flags, winner, weather, etc.

| Column | Type | Description |
|--------|------|-------------|
| `season` | INT | Season |
| `round_number` | INT | Round number |
| `meeting_official_name` | TEXT | Meeting name |
| `circuit_id` | TEXT | Circuit ID |
| `circuit_name` | TEXT | Circuit name |
| `circuit_short_name` | TEXT | Circuit short name |
| `session_id` | TEXT | Session ID |
| `session_type` | session_type_enum | Session type |
| `scheduled_laps` | INT | Scheduled laps |
| `start_time` | TIMESTAMPTZ | Start time |
| `end_time` | TIMESTAMPTZ | End time |
| `completed_laps` | INT | Completed laps |
| `winner_driver_id` | TEXT | Winner driver ID |
| `winner_team_id` | TEXT | Winner team ID |
| `safety_car_laps` | INT | Safety car lap count |
| `vsc_laps` | INT | VSC lap count |
| `red_flag_count` | INT | Red flag count |
| `classified_finishers` | INT | Classified finishers |
| `avg_track_temp_c` | NUMERIC | Avg track temp |
| `max_track_temp_c` | NUMERIC | Max track temp |
| `avg_air_temp_c` | NUMERIC | Avg air temp |
| `max_air_temp_c` | NUMERIC | Max air temp |
| `rain_flag` | BOOLEAN | Rain occurred |
| `overtakes_count` | INT | Total overtakes |

**Indexes:**
- `idx_session_summary_session` on (session_id)
- `idx_session_summary_season` on (season)
- `idx_session_summary_session_type` on (session_type)

### Lap-Level Views

#### 6. `gold.lap_times`
Canonical per-lap timing table.

**Purpose**: Race traces, stint analysis, pace comparisons.

| Column | Type | Description |
|--------|------|-------------|
| `season` | INT | Season |
| `round_number` | INT | Round number |
| `meeting_official_name` | TEXT | Meeting name |
| `session_type` | session_type_enum | Session type |
| `session_id` | TEXT | Session ID |
| `driver_id` | TEXT | Driver ID |
| `driver_number` | INT | Driver number |
| `driver_name` | TEXT | Driver name |
| `name_acronym` | CHAR(3) | Driver acronym |
| `team_id` | TEXT | Team ID |
| `team_name` | TEXT | Team name |
| `display_name` | TEXT | Display name |
| `color_hex` | TEXT | Team color |
| `lap_number` | INT | Lap number |
| `date_start` | TIMESTAMPTZ | Lap start time |
| `lap_duration_ms` | INT | Lap time (ms) |
| `duration_s1_ms` | INT | S1 time (ms) |
| `duration_s2_ms` | INT | S2 time (ms) |
| `duration_s3_ms` | INT | S3 time (ms) |
| `i1_speed_kph` | NUMERIC(6,2) | I1 speed |
| `i2_speed_kph` | NUMERIC(6,2) | I2 speed |
| `st_speed_kph` | NUMERIC(6,2) | Speed trap |
| `is_pit_in_lap` | BOOLEAN | Pit in lap |
| `is_pit_out_lap` | BOOLEAN | Pit out lap |
| `is_valid` | BOOLEAN | Valid lap |
| `lap_time_s` | NUMERIC | Lap time (seconds) |
| `cumulative_time_ms` | BIGINT | Cumulative time |

**Indexes:**
- `idx_lap_times_session_driver_lap` on (session_id, driver_id, lap_number)
- `idx_lap_times_season` on (season)
- `idx_lap_times_session_type` on (session_type)

#### 7. `gold.lap_intervals`
Lap-by-lap gap and interval data.

**Purpose**: Position-by-lap charts.

| Column | Type | Description |
|--------|------|-------------|
| `season` | INT | Season |
| `round_number` | INT | Round number |
| `meeting_official_name` | TEXT | Meeting name |
| `session_type` | session_type_enum | Session type |
| `session_id` | TEXT | Session ID |
| `driver_id` | TEXT | Driver ID |
| `driver_number` | INT | Driver number |
| `driver_name` | TEXT | Driver name |
| `name_acronym` | CHAR(3) | Driver acronym |
| `team_id` | TEXT | Team ID |
| `team_name` | TEXT | Team name |
| `display_name` | TEXT | Display name |
| `color_hex` | TEXT | Team color |
| `lap_number` | INT | Lap number |
| `gap_to_leader_ms` | INT | Gap to leader (ms) |
| `interval_ms` | INT | Interval (ms) |
| `gap_to_leader_s` | NUMERIC | Gap to leader (s) |
| `interval_s` | NUMERIC | Interval (s) |
| `position` | INT | Position |

**Indexes:**
- `idx_lap_intervals_session_driver_lap` on (session_id, driver_id, lap_number)
- `idx_lap_intervals_season` on (season)
- `idx_lap_intervals_session_type` on (session_type)

### Dimension Views

#### 8. `gold.dim_drivers`
Driver dimension table with season-specific attributes.

**Purpose**: Driver identities, numbers, teams, headshots.

| Column | Type | Description |
|--------|------|-------------|
| `driver_id` | TEXT | Driver ID |
| `driver_number` | INT | Racing number |
| `full_name` | TEXT | Full name |
| `name_acronym` | CHAR(3) | 3-letter acronym |
| `country_code` | CHAR(3) | Nationality |
| `headshot_url` | TEXT | Headshot URL |
| `headshot_override` | TEXT | Override headshot |
| `wikipedia_url` | TEXT | Wikipedia ID |
| `birthdate` | TIMESTAMPTZ | Birth date |
| `season` | INT | Season |
| `primary_team_id` | TEXT | Primary team |
| `primary_team_name` | TEXT | Team name |

**Indexes:**
- `idx_dim_drivers_driver_id` on (driver_id)
- `idx_dim_drivers_season` on (season)
- `idx_dim_drivers_driver_season` on (driver_id, season)

#### 9. `gold.dim_teams`
Team dimension table with branding.

**Purpose**: Team identities, colors, logos over time.

| Column | Type | Description |
|--------|------|-------------|
| `team_id` | TEXT | Team ID |
| `team_name` | TEXT | Team name |
| `display_name` | TEXT | Display name |
| `color_hex` | TEXT | Primary color |
| `logo_url` | TEXT | Logo URL |
| `season` | INT | Season |

**Indexes:**
- `idx_dim_teams_team_id` on (team_id)
- `idx_dim_teams_season` on (season)
- `idx_dim_teams_team_season` on (team_id, season)

#### 10. `gold.dim_meetings`
Meeting/Grand Prix dimension table.

**Purpose**: Meeting metadata with circuit and country.

| Column | Type | Description |
|--------|------|-------------|
| `meeting_id` | TEXT | Meeting ID |
| `season` | INT | Season |
| `round_number` | INT | Round number |
| `meeting_official_name` | TEXT | Official name |
| `meeting_short_name` | TEXT | Short name |
| `circuit_name` | TEXT | Circuit name |
| `circuit_short_name` | TEXT | Circuit short name |
| `location` | TEXT | Location |
| `country_code` | CHAR(3) | Country code |
| `country_name` | TEXT | Country name |
| `flag_url` | TEXT | Flag URL |
| `date_start` | TIMESTAMPTZ | Start date |
| `date_end` | TIMESTAMPTZ | End date |

**Indexes:**
- `idx_dim_meetings_meeting_id` on (meeting_id)
- `idx_dim_meetings_season` on (season)
- `idx_dim_meetings_season_meeting` on (season, meeting_id)

#### 11. `gold.dim_circuits`
Circuit dimension table with characteristics.

**Purpose**: Circuit geography, lap records, usage stats.

| Column | Type | Description |
|--------|------|-------------|
| `circuit_id` | TEXT | Circuit ID |
| `circuit_name` | TEXT | Circuit name |
| `circuit_short_name` | TEXT | Short name |
| `location` | TEXT | Location |
| `country_code` | CHAR(3) | Country code |
| `country_name` | TEXT | Country name |
| `flag_url` | TEXT | Flag URL |
| `lat` | NUMERIC(9,6) | Latitude |
| `lon` | NUMERIC(9,6) | Longitude |
| `lap_length_km` | NUMERIC(6,3) | Lap length (km) |
| `race_laps` | INT | Race laps |
| `race_distance_km` | NUMERIC | Race distance (km) |
| `sprint_laps` | INT | Sprint laps |
| `sprint_distance_km` | NUMERIC | Sprint distance (km) |
| `last_year_used` | INT | Last year used |
| `total_turns` | INT | Total turns (TODO) |
| `fastest_lap_time_ms` | INT | Lap record (ms) |
| `fastest_lap_driver_id` | TEXT | Record holder |
| `fastest_lap_driver_name` | TEXT | Record holder name |
| `fastest_lap_driver_name_acronym` | CHAR(3) | Acronym |
| `fastest_lap_year` | INT | Record year |
| `last_race_season` | INT | Last race season |
| `last_race_session_id` | TEXT | Last race session |
| `last_meeting_id` | TEXT | Last meeting |

**Indexes:**
- `idx_dim_circuits_circuit_id` on (circuit_id)
- `idx_dim_circuits_country_code` on (country_code)

#### 12. `gold.circuit_overtake_stats`
Circuit overtake statistics.

**Purpose**: Aggregate overtake stats per circuit.

| Column | Type | Description |
|--------|------|-------------|
| `circuit_id` | TEXT | Circuit ID |
| `circuit_name` | TEXT | Circuit name |
| `overtakes_race_avg` | NUMERIC | Avg overtakes (race) |
| `overtakes_sprint_avg` | NUMERIC | Avg overtakes (sprint) |
| `overtakes_race_record` | INT | Record overtakes (race) |
| `overtakes_sprint_record` | INT | Record overtakes (sprint) |

**Indexes:**
- `idx_circuit_overtake_stats_circuit_id` on (circuit_id)

---

## Enumerated Types

The database uses the following custom enum types in the `silver` schema:

### 1. `silver.session_type_enum`
Valid session types.

```sql
('p1', 'p2', 'p3', 'quali', 'sprint_quali', 'sprint', 'race')
```

### 2. `silver.points_awarding_enum`
Points awarding categories.

```sql
('none', 'sprint', 'race')
```

### 3. `silver.completion_band_enum`
Race completion bands for points system.

```sql
('0_to_25_PCT', '25_to_50_PCT', '50_to_75_PCT', '100_PCT')
```

### 4. `silver.status_enum`
Driver status at end of session.

```sql
('dns', 'dnf', 'dsq', 'finished', 'nc')
```

- `dns`: Did Not Start
- `dnf`: Did Not Finish
- `dsq`: Disqualified
- `finished`: Finished the session
- `nc`: Not Classified

### 5. `silver.bonus_enum`
Bonus points types.

```sql
('fastest_lap')
```

### 6. `silver.tyre_compound_enum`
Tyre compounds.

```sql
('soft', 'medium', 'hard', 'intermediate', 'wet')
```

---

## Entity Relationship Diagram

### Core Entity Relationships

```
countries
    ↓ (1:N)
circuits ← (1:N) → meetings
                      ↓ (1:N)
                  sessions
                      ↓ (1:N)
    ┌─────────────────┴──────────────────┐
    ↓                 ↓                   ↓
results           laps              race_control
stints         intervals           pit_stops
overtakes      position            car_telemetry
weather        car_gps

drivers ← (1:N) → driver_numbers_by_season
   ↓                      ↓
   └──── driver_teams_by_session ────┐
                  ↓                    ↓
              sessions              teams
                                      ↓
                              team_branding
```

### Key Foreign Key Relationships

**Countries & Circuits:**
- `circuits.country_code` → `countries.country_code`
- `drivers.country_code` → `countries.country_code`

**Meetings & Sessions:**
- `meetings.circuit_id` → `circuits.circuit_id`
- `sessions.meeting_id` → `meetings.meeting_id`

**Drivers & Teams:**
- `driver_numbers_by_season.driver_id` → `drivers.driver_id`
- `driver_teams_by_session.driver_id` → `drivers.driver_id`
- `driver_teams_by_session.team_id` → `teams.team_id`
- `driver_teams_by_session.session_id` → `sessions.session_id`
- `team_branding.team_id` → `teams.team_id`

**Session Data:**
- `results.session_id` → `sessions.session_id`
- `results.driver_id` → `drivers.driver_id`
- `laps.session_id` → `sessions.session_id`
- `laps.driver_id` → `drivers.driver_id`
- `stints.lap_start_id` → `laps.lap_id`
- `stints.lap_end_id` → `laps.lap_id`
- `pit_stops.lap_id` → `laps.lap_id`
- `race_control.referenced_lap_id` → `laps.lap_id`

**Telemetry:**
- `car_telemetry.session_id` → `sessions.session_id`
- `car_telemetry.driver_id` → `drivers.driver_id`
- `car_gps.session_id` → `sessions.session_id`
- `car_gps.driver_id` → `drivers.driver_id`

---

## Indexes

### Silver Layer Indexes

No explicit indexes are created in the silver layer creation script (indexes are managed separately or via constraints).

### Gold Layer Indexes

All gold layer materialized views have indexes for performance:

#### Driver Standings Progression
- `idx_driver_standings_progression_season_driver` on (season, driver_id)
- `idx_driver_standings_progression_session` on (session_id)

#### Constructor Standings Progression
- `idx_constructor_standings_progression_season_team` on (season, team_id)
- `idx_constructor_standings_progression_session` on (session_id)

#### Driver Session Results
- `idx_driver_session_results_session_driver` on (session_id, driver_id)
- `idx_driver_session_results_season` on (season)
- `idx_driver_session_results_session_type` on (session_type)

#### Session Classification
- `idx_session_classification_session_driver` on (session_id, driver_id)
- `idx_session_classification_season` on (season)
- `idx_session_classification_session_type` on (session_type)

#### Session Summary
- `idx_session_summary_session` on (session_id)
- `idx_session_summary_season` on (season)
- `idx_session_summary_session_type` on (session_type)

#### Lap Times
- `idx_lap_times_session_driver_lap` on (session_id, driver_id, lap_number)
- `idx_lap_times_season` on (season)
- `idx_lap_times_session_type` on (session_type)

#### Lap Intervals
- `idx_lap_intervals_session_driver_lap` on (session_id, driver_id, lap_number)
- `idx_lap_intervals_season` on (season)
- `idx_lap_intervals_session_type` on (session_type)

#### Dimension Tables
- `idx_dim_drivers_driver_id` on (driver_id)
- `idx_dim_drivers_season` on (season)
- `idx_dim_drivers_driver_season` on (driver_id, season)
- `idx_dim_teams_team_id` on (team_id)
- `idx_dim_teams_season` on (season)
- `idx_dim_teams_team_season` on (team_id, season)
- `idx_dim_meetings_meeting_id` on (meeting_id)
- `idx_dim_meetings_season` on (season)
- `idx_dim_meetings_season_meeting` on (season, meeting_id)
- `idx_dim_circuits_circuit_id` on (circuit_id)
- `idx_dim_circuits_country_code` on (country_code)
- `idx_circuit_overtake_stats_circuit_id` on (circuit_id)

---

## Usage Notes

### Data Flow
1. **Ingestion**: Python scripts in `pitwall_ingest/` pull data from OpenF1 API → Bronze layer
2. **Transformation**: Python scripts in `pitwall_silver/` clean and enrich → Silver layer
3. **Aggregation**: SQL views automatically aggregate → Gold layer
4. **Consumption**: FastAPI (`api/main.py`) and React frontend query Gold layer

### Refreshing Gold Layer
Gold layer materialized views need to be refreshed after silver data updates:

```sql
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

### Key Design Patterns

1. **Medallion Architecture**: Bronze (raw) → Silver (clean) → Gold (aggregated)
2. **Immutable Bronze**: Bronze tables never update, only insert with new `ingested_at`
3. **Idempotent Silver**: Silver upserts use UPSERT/ON CONFLICT patterns
4. **Materialized Gold**: Gold views are materialized for performance
5. **Helper Views**: `driver_id_by_session` simplifies joins across session data

---

## Maintenance Scripts

### Ingestion Scripts
Located in `pitwall_ingest/`:
- `ingest_meetings.py`
- `ingest_sessions.py`
- `ingest_drivers.py`
- `ingest_laps.py`
- `ingest_results.py`
- `ingest_car_telemetry.py`
- `ingest_car_gps.py`
- ...and more

### Transformation Scripts
Located in `pitwall_silver/`:
- `upsert_meetings.py`
- `upsert_sessions.py`
- `upsert_drivers.py`
- `upsert_laps.py`
- `upsert_results.py`
- `upsert_car_telemetry.py`
- `upsert_car_gps.py`
- ...and more

### Orchestration
- `orchestrate_ingestion.py`: Orchestrates full ingestion pipeline
- `run_high_volume_upserts.py`: Manages high-volume telemetry upserts

---

## Contact & Contributions

For questions or contributions, please refer to the main README.md in the project root.



