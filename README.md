# Pitwall Database Setup

This project uses a PostgreSQL database running in Docker, completely isolated from any existing Postgres instances on your machine.

## Starting the Database

To start the database:

```bash
docker compose up -d
```

To stop the database:

```bash
docker compose down
```

To stop and remove all data:

```bash
docker compose down -v
```

## Connection Details

The database is accessible on **port 5433** (to avoid conflicts with any existing Postgres on port 5432).

### Connection String

```
postgresql://pitwall:pitwall@localhost:5433/pitwall
```

### Environment Variables

Copy `.env.example` to `.env` and use these values:

- `PGHOST=localhost`
- `PGPORT=5433`
- `PGDATABASE=pitwall`
- `PGUSER=pitwall`
- `PGPASSWORD=pitwall`

## Database Structure

### Role

- **pitwall**: Non-superuser role with password `pitwall`
- Default search_path: `"$user", bronze, silver, gold, public`

### Database

- **pitwall**: Owned by the `pitwall` role

### Schemas

- **bronze**: Full usage and creation rights for `pitwall` role
- **silver**: Full usage and creation rights for `pitwall` role
- **gold**: Full usage and creation rights for `pitwall` role
- **public**: Usage only (CREATE revoked from public)

## Admin Access

If you need admin access, use:

- User: `pitwall_admin`
- Password: `pitwall_admin`
- Database: `pitwall`
- Port: `5433`

## Data Ingestion

### Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` (if not already done):
   ```bash
   cp .env.example .env
   ```

### Running Ingest Scripts

Ingest scripts are located in the `pitwall_ingest/` directory. Each script pulls data from OpenF1 API endpoints and inserts into the corresponding bronze table.

**Example: Ingest meetings data**
```bash
python pitwall_ingest/ingest_meetings.py
```

### Rate Limiting

All ingest scripts include:
- Default 0.5s delay between requests
- Automatic retry on 429 (rate limit) errors
- Maximum 5 retries before alerting
- If rate limiting persists, increase `RATE_LIMIT_DELAY` in the script

### Available Ingest Scripts

- `ingest_meetings.py` - Ingest meetings data into `bronze.meetings_raw`

