import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
  selectedSeason: number | null;
  selectedSession: string | null;
  selectedDriver: string | null;
  sidebarOpen: boolean;
  sidebarWidth: number;
  setSelectedSeason: (season: number | null) => void;
  setSelectedSession: (session: string | null) => void;
  setSelectedDriver: (driver: string | null) => void;
  setSidebarOpen: (open: boolean) => void;
  setSidebarWidth: (width: number) => void;
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      selectedSeason: null,
      selectedSession: null,
      selectedDriver: null,
      sidebarOpen: false, // Closed by default
      sidebarWidth: 240, // Default sidebar width
      setSelectedSeason: (season) => set({ selectedSeason: season }),
      setSelectedSession: (session) => set({ selectedSession: session }),
      setSelectedDriver: (driver) => set({ selectedDriver: driver }),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setSidebarWidth: (width) => set({ sidebarWidth: width }),
    }),
    {
      name: 'pitwall-storage', // localStorage key
      partialize: (state) => ({ 
        sidebarOpen: state.sidebarOpen,
        sidebarWidth: state.sidebarWidth,
      }), // Only persist sidebar state
    }
  )
);

