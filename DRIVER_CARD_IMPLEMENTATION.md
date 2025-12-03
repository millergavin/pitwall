# Driver Card Implementation Summary

## 🎨 Design Specifications

### Background
- **Base color**: Team color hex from database
- **Gradient overlay**: Linear gradient (left to right)
  - Left: Black 50% opacity
  - Right: Black 0% opacity

### Driver Name
- **Layout**: First name on top, last name below
- **Case**: Title Case (e.g., "Max Verstappen")
- **Color**: White
- **Shadow**: Subtle drop shadow (0 2px 4px rgba(0,0,0,0.3))
- **Fonts**:
  - First name: Formula 1 Display Regular
  - Last name: Formula 1 Display Bold

### Driver Number
- **Font**: Formula 1 Display Regular
- **Size**: 120px
- **Color**: Black with 20% opacity
- **Style**: Large overlay background graphic
- **Shadow**: None

### Driver Photo
- **Source**: `headshot_override` (falls back to `headshot_url`)
- **Aspect**: Container is ~3:4 aspect ratio
- **Alignment**: Top-aligned
- **Crop**: Shows waist-up, cut off at bottom of card

### Team Logo
- **Location**: Small badge in bottom-left corner
- **Style**: White logo on black 50% opacity circular background
- **Size**: 40px container, 24px logo

## 📁 Files Created/Modified

### New Files

#### 1. `/frontend/src/components/DriverCard.tsx`
- Complete driver card component with all styling
- Handles image errors gracefully
- Supports click interactions
- Responsive design (16:9 aspect ratio)

#### 2. `/frontend/src/pages/Drivers.tsx`
- Driver roster page with grid layout
- Season selector
- Loading and error states
- Empty state handling

#### 3. `/api/main.py` (Modified - added endpoint)
- New endpoint: `GET /api/drivers/roster?season=YYYY`
- Returns 20 permanent drivers for the season
- Includes latest team information per driver
- Ordered by driver number

### Modified Files

#### 4. `/frontend/src/api/client.ts`
- Added `driversRoster()` method
- Accepts season parameter (defaults to 2025)

#### 5. `/frontend/tailwind.config.js`
- Added `font-f1-display-regular` font family
- Added `font-f1-display-bold` font family

## 🔧 API Endpoint

### `/api/drivers/roster`

**Query Parameters:**
- `season` (int, optional): Default 2025

**Returns:** Array of driver objects
```typescript
{
  driver_id: string;
  driver_number: number;
  first_name: string;
  last_name: string;
  full_name: string;
  name_acronym: string;
  headshot_url: string | null;
  headshot_override: string | null;
  team_id: string;
  team_name: string;
  color_hex: string;
  team_logo_url: string | null;
}
```

**Logic:**
1. Counts sessions per driver in the season
2. Returns top 20 drivers by session count (permanent roster)
3. For each driver, returns their most recent team information
4. Orders by driver number

## 🎯 Database Query Strategy

The API endpoint uses this strategy to get current roster:

```sql
WITH driver_session_counts AS (
    -- Get drivers with most sessions (top 20)
    SELECT driver_id, COUNT(DISTINCT session_id) as session_count
    FROM gold.driver_standings_progression
    WHERE season = :season
    GROUP BY driver_id
    ORDER BY session_count DESC
    LIMIT 20
),
latest_driver_info AS (
    -- Get most recent appearance for styling
    SELECT DISTINCT ON (driver_id) ...
    ORDER BY driver_id, round_number DESC
)
```

This ensures:
- Only permanent drivers (not reserve/replacement drivers)
- Most recent team colors and logos
- One entry per driver

## 🚀 Usage

### In a Page Component
```typescript
import { DriverCard } from '../components/DriverCard';
import { api } from '../api/client';

const drivers = await api.driversRoster(2025);

<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
  {drivers.map(driver => (
    <DriverCard 
      key={driver.driver_id}
      driver={driver}
      onClick={() => handleDriverClick(driver)}
    />
  ))}
</div>
```

### Routes
- The `/drivers` route is already configured in `App.tsx`
- Navigate to `/drivers` to see the driver roster page

## ✅ Features

- [x] Team color backgrounds with gradient overlay
- [x] Formula 1 Display fonts (Regular + Bold)
- [x] Title case name formatting
- [x] Large background driver numbers
- [x] Driver headshots with fallback
- [x] Team logo badges
- [x] Hover effects
- [x] Responsive grid layout
- [x] Season selector
- [x] Loading states
- [x] Error handling
- [x] Empty state

## 🎨 Component Props

```typescript
interface DriverCardProps {
  driver: DriverCardData;
  onClick?: () => void;
}

interface DriverCardData {
  driver_id: string;
  driver_number: number;
  first_name: string;
  last_name: string;
  full_name: string;
  name_acronym: string;
  headshot_url: string | null;
  headshot_override: string | null;
  team_id: string;
  team_name: string;
  color_hex: string;
  team_logo_url: string | null;
}
```

## 🔥 Next Steps (Optional Enhancements)

1. **Driver Detail Page**: Click on card → navigate to detailed driver stats
2. **Filtering**: Filter by team, nationality, etc.
3. **Sorting**: Sort by name, number, team
4. **Search**: Search drivers by name
5. **Animations**: Entry animations for cards
6. **Career Stats**: Add brief career stats on hover
7. **Social Links**: Add driver social media links

## 🐛 Notes

- Color hex values from database don't include "#" prefix - component handles this
- API runs on port 8001 (Vite proxy configured)
- Fonts are pre-loaded from `/assets/fonts/`
- Team logos are SVG icons in `/assets/team_logos/icons/`
