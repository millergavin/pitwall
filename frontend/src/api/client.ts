// In production, use the full API URL; in dev, use Vite proxy
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const api = {
  drivers: async (season?: number) => {
    const url = new URL(`${API_BASE_URL}/drivers`, window.location.origin);
    if (season) {
      url.searchParams.append('season', season.toString());
    }
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  driversRoster: async (season: number = 2025) => {
    const url = new URL(`${API_BASE_URL}/drivers/roster`, window.location.origin);
    url.searchParams.append('season', season.toString());
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  driverDetail: async (driverId: string, season: number = 2025) => {
    const url = new URL(`${API_BASE_URL}/drivers/${driverId}`, window.location.origin);
    url.searchParams.append('season', season.toString());
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  teamDetail: async (teamId: string, season: number = 2025) => {
    const url = new URL(`${API_BASE_URL}/teams/${teamId}`, window.location.origin);
    url.searchParams.append('season', season.toString());
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  teamsRoster: async (season: number = 2025) => {
    const url = new URL(`${API_BASE_URL}/teams/roster`, window.location.origin);
    url.searchParams.append('season', season.toString());
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  standings: {
    drivers: async (season: number = 2024) => {
      const url = new URL(`${API_BASE_URL}/standings/drivers`, window.location.origin);
      url.searchParams.append('season', season.toString());
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },

    constructors: async (season: number = 2024) => {
      const url = new URL(`${API_BASE_URL}/standings/constructors`, window.location.origin);
      url.searchParams.append('season', season.toString());
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },
  },

  circuits: async () => {
    const url = new URL(`${API_BASE_URL}/circuits`, window.location.origin);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  images: async (options?: {
    circuitId?: string;
    driverId?: string;
    teamId?: string;
    meetingId?: string;
    imageType?: string;
    tag?: string;
    year?: number;
    coverOnly?: boolean;
  }) => {
    const url = new URL(`${API_BASE_URL}/images`, window.location.origin);
    if (options?.circuitId) url.searchParams.append('circuit_id', options.circuitId);
    if (options?.driverId) url.searchParams.append('driver_id', options.driverId);
    if (options?.teamId) url.searchParams.append('team_id', options.teamId);
    if (options?.meetingId) url.searchParams.append('meeting_id', options.meetingId);
    if (options?.imageType) url.searchParams.append('image_type', options.imageType);
    if (options?.tag) url.searchParams.append('tag', options.tag);
    if (options?.year) url.searchParams.append('year', options.year.toString());
    if (options?.coverOnly) url.searchParams.append('cover_only', 'true');
    
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  meetings: async (season?: number) => {
    const url = new URL(`${API_BASE_URL}/meetings`, window.location.origin);
    if (season) {
      url.searchParams.append('season', season.toString());
    }
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  meeting: async (meetingId: string) => {
    const url = new URL(`${API_BASE_URL}/meetings/${meetingId}`, window.location.origin);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  meetingSessions: async (meetingId: string) => {
    const url = new URL(`${API_BASE_URL}/meetings/${meetingId}/sessions`, window.location.origin);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  session: async (sessionId: string) => {
    const url = new URL(`${API_BASE_URL}/sessions/${sessionId}`, window.location.origin);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  sessionClassification: async (sessionId: string) => {
    const url = new URL(`${API_BASE_URL}/sessions/${sessionId}/classification`, window.location.origin);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  // Database management
  database: {
    status: async () => {
      const url = new URL(`${API_BASE_URL}/database/status`, window.location.origin);
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },

    update: async (skipHighVolume: boolean = true) => {
      const url = new URL(`${API_BASE_URL}/database/update`, window.location.origin);
      url.searchParams.append('skip_high_volume', skipHighVolume.toString());
      const response = await fetch(url.toString(), { method: 'POST' });
      if (!response.ok) {
        if (response.status === 409) {
          throw new Error('Database update already in progress');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },

    refreshGold: async () => {
      const url = new URL(`${API_BASE_URL}/database/refresh-gold`, window.location.origin);
      const response = await fetch(url.toString(), { method: 'POST' });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },
  },
};
