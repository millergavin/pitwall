// In production, use the full API URL; in dev, use Vite proxy
// Default to production API URL if not set (for Vercel deployments)
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.PROD ? 'https://api.pitwall.one/api' : '/api');

// Helper to construct API URLs
const getApiUrl = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  
  // If API_BASE_URL is a full URL (starts with http), use it directly
  if (API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')) {
    return `${API_BASE_URL}${cleanPath}`;
  }
  // Otherwise, return the relative path (will be used with window.location.origin)
  return `${API_BASE_URL}${cleanPath}`;
};

// Helper to create a URL object, handling both absolute and relative URLs
const createApiUrl = (path: string): URL => {
  const urlString = getApiUrl(path);
  // If it's already an absolute URL, new URL will ignore the base
  return new URL(urlString, window.location.origin);
};

export const api = {
  drivers: async (season?: number) => {
    const url = createApiUrl('/drivers');
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
    const url = createApiUrl('/drivers/roster');
    url.searchParams.append('season', season.toString());
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  driverDetail: async (driverId: string, season: number = 2025) => {
    const url = createApiUrl(`/drivers/${driverId}`);
    url.searchParams.append('season', season.toString());
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  teamDetail: async (teamId: string, season: number = 2025) => {
    const url = createApiUrl(`/teams/${teamId}`);
    url.searchParams.append('season', season.toString());
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  teamsRoster: async (season: number = 2025) => {
    const url = createApiUrl('/teams/roster');
    url.searchParams.append('season', season.toString());
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  standings: {
    drivers: async (season: number = 2024) => {
      const url = createApiUrl('/standings/drivers');
      url.searchParams.append('season', season.toString());
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },

    constructors: async (season: number = 2024) => {
      const url = createApiUrl('/standings/constructors');
      url.searchParams.append('season', season.toString());
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },
  },

  circuits: async () => {
    const url = createApiUrl('/circuits');
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
    const url = createApiUrl('/images');
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
    const url = createApiUrl('/meetings');
    if (season) {
      url.searchParams.append('season', season.toString());
    }
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  seasons: async (): Promise<number[]> => {
    const url = createApiUrl('/seasons');
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  meeting: async (meetingId: string) => {
    const url = createApiUrl(`/meetings/${meetingId}`);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  meetingSessions: async (meetingId: string) => {
    const url = createApiUrl(`/meetings/${meetingId}/sessions`);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  session: async (sessionId: string) => {
    const url = createApiUrl(`/sessions/${sessionId}`);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  sessionClassification: async (sessionId: string) => {
    const url = createApiUrl(`/sessions/${sessionId}/classification`);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  lapChart: async (sessionId: string) => {
    const url = createApiUrl(`/sessions/${sessionId}/lap-chart`);
    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  },

  // Database management
  database: {
    status: async () => {
      const url = createApiUrl('/database/status');
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },

    update: async (skipHighVolume: boolean = true) => {
      const url = createApiUrl('/database/update');
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
      const url = createApiUrl('/database/refresh-gold');
      const response = await fetch(url.toString(), { method: 'POST' });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },

    dockerStatus: async () => {
      const url = createApiUrl('/database/docker-status');
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },

    startDocker: async () => {
      const url = createApiUrl('/database/start-docker');
      const response = await fetch(url.toString(), { method: 'POST' });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    },
  },
};
