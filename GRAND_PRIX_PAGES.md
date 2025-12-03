# Grand Prix Pages Implementation

This document summarizes the Grand Prix page structure implementation for Pitwall.

## Overview

We've created a three-level navigation structure for Grand Prix data:
1. **Grand Prix List** - Shows all meetings (Grand Prix) for a selected season
2. **Meeting Details** - Shows details about a specific meeting and lists its sessions
3. **Session Details** - Shows detailed results and classification for a specific session

## Pages Created

### 1. GrandPrix (List Page)
- **Route**: `/grand-prix`
- **File**: `frontend/src/pages/GrandPrix.tsx`
- **Features**:
  - Season selector (defaults to 2024)
  - Grid of meeting cards with circuit cover images
  - Each card shows: round number, flag, date range, meeting name, and circuit name
  - Clicking a card navigates to the meeting details page

### 2. MeetingDetails
- **Route**: `/grand-prix/:meetingId`
- **File**: `frontend/src/pages/MeetingDetails.tsx`
- **Features**:
  - Hero section with circuit cover image and meeting info
  - Meeting metadata: location, country, date range
  - List of all sessions for the meeting (Practice, Qualifying, Sprint, Race)
  - Session cards show session type, start time, and winner (if available)
  - Clicking a session navigates to the session details page

### 3. SessionDetails
- **Route**: `/sessions/:sessionId`
- **File**: `frontend/src/pages/SessionDetails.tsx`
- **Features**:
  - Session header with winner information
  - Session statistics: circuit, start time, laps, weather, temperatures
  - Flag indicators (red, yellow, safety car, VSC)
  - Full classification table with:
    - Position, driver number, driver name, team
    - For races: laps, time/DNF reason, points
    - For qualifying: fastest time, gap, total laps

## Components Created

### MeetingCard
- **File**: `frontend/src/components/MeetingCard.tsx`
- **Purpose**: Display a meeting in the Grand Prix list
- **Design**: Card with circuit cover image, gradient overlay, round badge, flag, date range, and names

## API Endpoints Added

### Backend (Python/FastAPI)
- `GET /api/meetings/{meeting_id}` - Get a specific meeting
- `GET /api/meetings/{meeting_id}/sessions` - Get all sessions for a meeting
- `GET /api/sessions/{session_id}` - Get session summary
- `GET /api/sessions/{session_id}/classification` - Get session results

### Frontend API Client
- `api.meetings(season?)` - Get all meetings, optionally filtered by season
- `api.meeting(meetingId)` - Get a specific meeting
- `api.meetingSessions(meetingId)` - Get sessions for a meeting
- `api.session(sessionId)` - Get session summary
- `api.sessionClassification(sessionId)` - Get session classification/results

## Database Changes

### Updated gold.session_summary View
Added the following fields:
- `meeting_id` - Link to the meeting
- `winner_driver_name` - Winner's name
- `winner_team_name` - Winner's team name
- `yellow_flag_count` - Count of yellow flags
- `safety_car_count` - Count of safety car deployments
- `virtual_safety_car_count` - Count of VSC deployments
- `weather_conditions` - Most common weather description
- `air_temperature` - Average air temperature
- `track_temperature` - Average track temperature

## Navigation Updates

- **NavSidebar**: Updated to replace "Races" link with "Grand Prix" link
- **App.tsx**: Updated routes to include:
  - `/grand-prix` - Grand Prix list
  - `/grand-prix/:meetingId` - Meeting details
  - `/sessions/:sessionId` - Session details

## Design Patterns

All pages follow the existing Pitwall design system:
- F1 typography (f1-display-bold, f1-display-regular)
- Consistent card styling with rounded corners
- Gradient overlays for hero images
- Zinc color palette for backgrounds
- F1 red (#FF1E00) for accent elements
- Hover states and transitions
- Loading and error states

## Files Modified

1. `/api/main.py` - Added new endpoints
2. `/frontend/src/api/client.ts` - Added API methods
3. `/frontend/src/App.tsx` - Updated routes
4. `/frontend/src/components/NavSidebar.tsx` - Updated navigation
5. `/init-db/05-create-gold-views.sql` - Enhanced session_summary view

## Files Created

1. `/frontend/src/pages/GrandPrix.tsx`
2. `/frontend/src/pages/MeetingDetails.tsx`
3. `/frontend/src/pages/SessionDetails.tsx`
4. `/frontend/src/components/MeetingCard.tsx`

## Files Removed

1. `/frontend/src/pages/Races.tsx` - Replaced by GrandPrix.tsx

## Next Steps

To use these new pages:

1. **Database**: Run the updated SQL migration to refresh the gold.session_summary view:
   ```sql
   REFRESH MATERIALIZED VIEW gold.session_summary;
   ```

2. **Backend**: Restart the FastAPI server to pick up the new endpoints

3. **Frontend**: The pages are ready to use - navigate to `/grand-prix` to start exploring!

## User Flow

```
/grand-prix (season selector)
    ↓ [click on a Grand Prix card]
/grand-prix/:meetingId (meeting details & sessions list)
    ↓ [click on a session]
/sessions/:sessionId (session results & classification)
```

