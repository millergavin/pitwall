# Pitwall Frontend & API

This project consists of a FastAPI backend and React frontend for visualizing F1 data.

## Setup

### Backend API

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure your `.env` file is configured with database credentials (see main README.md)

3. Run the API server:
```bash
uvicorn api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI) will be available at `http://localhost:8000/docs`

### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file (optional, defaults to `http://localhost:8000`):
```bash
VITE_API_URL=http://localhost:8000
```

4. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5174`

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework (port 8000)
- **psycopg**: PostgreSQL adapter with connection pooling
- **Uvicorn**: ASGI server

### Frontend
- **React 19**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Zustand**: State management
- **Visx**: Data visualization (to be installed as needed)

## API Endpoints

- `GET /api/drivers?season=2023` - Get drivers
- `GET /api/teams?season=2023` - Get teams
- `GET /api/meetings?season=2023` - Get meetings
- `GET /api/circuits` - Get circuits
- `GET /api/session-summary?season=2023&session_type=race` - Get session summaries
- `GET /api/driver-standings?season=2023` - Get driver standings progression
- `GET /api/lap-times?session_id=...&driver_id=...` - Get lap times
- `GET /api/circuit-overtake-stats` - Get circuit overtake statistics

## Project Structure

```
pitwall/
├── api/
│   ├── __init__.py
│   └── main.py          # FastAPI application
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts    # API client
│   │   ├── store/
│   │   │   └── useStore.ts # Zustand store
│   │   ├── App.tsx
│   │   └── index.css
│   ├── tailwind.config.js
│   └── vite.config.ts
└── requirements.txt
```

## Installing Visx Packages

When you need to add visx charts, install packages individually:

```bash
cd frontend
npm install @visx/scale @visx/axis @visx/grid @visx/shape @visx/curve @visx/group
```

For tooltips and legends:
```bash
npm install @visx/tooltip @visx/legend
```

