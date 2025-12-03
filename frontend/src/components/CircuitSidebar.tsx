import type { FC } from 'react';

export interface CircuitData {
  circuit_id: string;
  circuit_name: string | null;
  circuit_short_name: string;
  location: string;
  country_code: string;
  country_name: string;
  flag_url: string;
  lat: number;
  lon: number;
  lap_length_km: number | null;
  race_laps: number | null;
  race_distance_km: number | null;
  sprint_laps: number | null;
  sprint_distance_km: number | null;
  last_year_used: number | null;
  total_turns: number | null;
  circuit_svg: string | null;
  fastest_lap_time_ms: number | null;
  fastest_lap_driver_id: string | null;
  fastest_lap_driver_name: string | null;
  fastest_lap_driver_name_acronym: string | null;
  fastest_lap_year: number | null;
}

interface CircuitSidebarProps {
  circuits: CircuitData[];
  selectedCircuit: CircuitData | null;
  coverImageUrl?: string | null;
  coverImagesMap?: Record<string, string>; // circuit_id -> image URL
  onSelectCircuit: (circuit: CircuitData | null) => void;
  onFlyToCircuit?: (circuit: CircuitData) => void;
  onNavigateToDetails?: (circuitId: string) => void;
}

// Format lap time from ms to mm:ss.sss
const formatLapTime = (ms: number): string => {
  const totalSeconds = ms / 1000;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toFixed(3).padStart(6, '0')}`;
};

// Convert km to miles
const kmToMiles = (km: number): number => km * 0.621371;

// Get display name for circuit
const getCircuitDisplayName = (circuit: CircuitData): string => {
  if (circuit.circuit_name) {
    return circuit.circuit_name;
  }
  // Use short name, but don't add "Circuit" if it already contains it
  if (circuit.circuit_short_name.toLowerCase().includes('circuit')) {
    return circuit.circuit_short_name;
  }
  return `${circuit.circuit_short_name} Circuit`;
};

// Get location display (avoid "Monaco, Monaco")
const getLocationDisplay = (circuit: CircuitData): string => {
  if (circuit.location === circuit.country_name) {
    return circuit.country_name;
  }
  return `${circuit.location}, ${circuit.country_name}`;
};

// Circuit List Item
const CircuitListItem: FC<{
  circuit: CircuitData;
  coverImageUrl?: string;
  onClick: () => void;
}> = ({ circuit, coverImageUrl, onClick }) => {
  return (
    <button
      type="button"
      className="flex items-center gap-3 w-full text-left cursor-pointer hover:bg-zinc-900 transition-colors group bg-transparent border-none outline-none appearance-none focus:outline-none focus:bg-overlay-100"
      style={{ padding: '1rem' }}
      onClick={onClick}
    >
      {/* Thumbnail */}
      <div className="w-16 h-12 rounded overflow-hidden flex-shrink-0 bg-zinc-900">
        {coverImageUrl ? (
          <img
            src={coverImageUrl}
            alt={circuit.circuit_short_name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-zinc-700 text-xs">
            No image
          </div>
        )}
      </div>
      
      {/* Text */}
      <div className="flex-1 min-w-0">
        <h3 className="f1-display-bold text-sm text-white truncate">
          {getCircuitDisplayName(circuit)}
        </h3>
        <p className="text-xs text-zinc-500 group-hover:text-white transition-colors truncate">
          {getLocationDisplay(circuit)}
        </p>
      </div>
    </button>
  );
};

// Circuit Detail View
const CircuitDetail: FC<{
  circuit: CircuitData;
  coverImageUrl?: string | null;
  onBack: () => void;
  onNavigateToDetails?: (circuitId: string) => void;
}> = ({ circuit, coverImageUrl, onBack, onNavigateToDetails }) => {
  return (
    <div className="flex flex-col h-full">
      {/* Header with cover image */}
      <div className="relative h-48 flex-shrink-0">
        {coverImageUrl ? (
          <img
            src={coverImageUrl}
            alt={circuit.circuit_short_name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-zinc-900" />
        )}
        
        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/20" />
        
        {/* Back button */}
        <button
          onClick={onBack}
          className="absolute top-3 left-3 text-white/70 hover:text-white transition-colors text-sm flex items-center gap-1"
          style={{ textShadow: '0 2px 8px rgba(0,0,0,0.8)' }}
        >
          <span>←</span>
          <span>All Circuits</span>
        </button>
        
        {/* Header text - make clickable */}
        <div className="absolute bottom-4 left-4 right-4">
          <button
            onClick={() => onNavigateToDetails?.(circuit.circuit_id)}
            className="text-left w-full hover:opacity-80 transition-opacity"
          >
            <h2 
              className="f1-display-bold text-xl text-white cursor-pointer"
              style={{ textShadow: '0 2px 8px rgba(0,0,0,0.8)' }}
            >
              {getCircuitDisplayName(circuit)}
            </h2>
            <p 
              className="text-sm text-zinc-300"
              style={{ textShadow: '0 1px 4px rgba(0,0,0,0.8)' }}
            >
              {getLocationDisplay(circuit)}
            </p>
          </button>
        </div>
      </div>
      
      {/* Circuit details */}
      <div className="flex-1 overflow-y-auto p-4 space-y-10">
        {/* Track SVG */}
        {circuit.circuit_svg && (
          <div className="p-8 bg-black rounded-corner">
            <img 
              src={circuit.circuit_svg}
              alt={`${circuit.circuit_short_name} track layout`}
              className="w-full h-auto max-h-[300px] object-contain"
            />
          </div>
        )}
        
        {/* Circuit Length */}
        {circuit.lap_length_km && (
          <div>
            <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wide">Circuit Length</p>
            <p className="f1-display-bold text-xl text-white leading-loose">
              {circuit.lap_length_km.toFixed(3)} <span className="normal-case">km</span>
            </p>
            <p className="f1-display-regular text-xl font-bold text-zinc-400">
              {kmToMiles(circuit.lap_length_km).toFixed(3)} <span className="normal-case">mi</span>
            </p>
          </div>
        )}
        
        {/* Number of Laps */}
        {circuit.race_laps && (
          <div>
            <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wide">Number of Laps</p>
            <p className="f1-display-bold text-xl text-white leading-loose">
              {circuit.race_laps}
            </p>
          </div>
        )}
        
        {/* Number of Turns */}
        {circuit.total_turns && (
          <div>
            <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wide">Number of Turns</p>
            <p className="f1-display-bold text-xl text-white leading-loose">
              {circuit.total_turns}
            </p>
          </div>
        )}
        
        {/* Fastest Lap Record */}
        {circuit.fastest_lap_time_ms && (
          <div>
            <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wide">Fastest Lap Record</p>
            <p className="f1-display-bold text-xl text-white leading-loose">
              {formatLapTime(circuit.fastest_lap_time_ms)}
            </p>
            {circuit.fastest_lap_driver_name && circuit.fastest_lap_year && (
              <p className="text-sm text-zinc-400 font-semibold">
                {circuit.fastest_lap_driver_name} ({circuit.fastest_lap_year})
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Main Sidebar Component
export const CircuitSidebar: FC<CircuitSidebarProps> = ({
  circuits,
  selectedCircuit,
  coverImageUrl,
  coverImagesMap = {},
  onSelectCircuit,
  onFlyToCircuit,
  onNavigateToDetails,
}) => {
  if (selectedCircuit) {
    return (
      <CircuitDetail
        circuit={selectedCircuit}
        coverImageUrl={coverImageUrl}
        onBack={() => onSelectCircuit(null)}
        onNavigateToDetails={onNavigateToDetails}
      />
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-zinc-800">
        <h2 className="f1-display-bold text-sm text-white">Circuits</h2>
        <p className="text-xs text-zinc-500">{circuits.length} circuits</p>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {circuits.map((circuit) => (
          <CircuitListItem
            key={circuit.circuit_id}
            circuit={circuit}
            coverImageUrl={coverImagesMap[circuit.circuit_id]}
            onClick={() => {
              onSelectCircuit(circuit);
              onFlyToCircuit?.(circuit);
            }}
          />
        ))}
      </div>
    </div>
  );
};

