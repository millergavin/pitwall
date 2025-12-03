import type { FC } from 'react';

interface StandingsDataPoint {
  season: number;
  round_number: number;
  meeting_name: string;
  meeting_short_name: string;
  country_code: string;
  emoji_flag: string;
  driver_id?: string;
  driver_number?: number;
  driver_name?: string;
  name_acronym?: string;
  team_id: string;
  team_name: string;
  display_name?: string;
  color_hex: string;
  logo_url?: string;
  cumulative_points: number;
}

interface StandingsTableProps {
  data: StandingsDataPoint[];
  type: 'drivers' | 'constructors';
  season: number;
  onHoverEntity?: (entityId: string | null) => void;
  hoveredEntityId?: string | null;
  selectedEntityIds?: Set<string>;
  onToggleEntity?: (entityId: string) => void;
  onResetSelection?: () => void;
  hoveredMeeting?: {
    round: number;
    name: string;
    emoji: string;
  } | null;
}

export const StandingsTable: FC<StandingsTableProps> = ({ 
  data, 
  type,
  season,
  onHoverEntity, 
  selectedEntityIds,
  onToggleEntity,
  onResetSelection,
  hoveredMeeting
}) => {
  if (!data || data.length === 0) {
    return <div className="text-zinc-600">No data available for this season.</div>;
  }

  // Determine which round to show (hovered meeting or latest)
  const targetRound = hoveredMeeting?.round ?? Math.max(...data.map(d => d.round_number));
  
  // Get standings for the target round
  const roundStandings = data
    .filter(d => d.round_number === targetRound)
    .sort((a, b) => b.cumulative_points - a.cumulative_points);
  
  // Calculate points added in the target round (difference from previous round)
  const standingsWithPointsAdded = roundStandings.map(standing => {
    const entityId = type === 'drivers' ? standing.driver_id : standing.team_id;
    const previousRoundData = data.find(
      d => d.round_number === targetRound - 1 && 
           (type === 'drivers' ? d.driver_id === entityId : d.team_id === entityId)
    );
    const pointsAdded = standing.cumulative_points - (previousRoundData?.cumulative_points || 0);
    return { ...standing, pointsAdded };
  });

  const hasSelections = selectedEntityIds && selectedEntityIds.size > 0;

  return (
    <div>
      {/* Header - Two Lines */}
      <div className="mb-4 h-[48px] flex flex-col justify-center">
        <h2 className="f1-display-bold text-sm leading-tight">
          <div>
            <span className="text-zinc-500">{season}</span>{' '}
            <span className="text-zinc-500">FORMULA 1</span>
          </div>
          <div className="text-white text-base">
            {hoveredMeeting 
              ? `${hoveredMeeting.name} ${hoveredMeeting.emoji}`
              : `WORLD ${type === 'drivers' ? "DRIVERS'" : "CONSTRUCTORS'"} CHAMPIONSHIP`
            }
          </div>
        </h2>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full table-auto border-collapse">
          <thead 
            className="bg-zinc-950 text-zinc-400 text-xs uppercase tracking-wide cursor-pointer hover:bg-zinc-900 transition-colors"
            onClick={onResetSelection}
            title="Click to reset selection"
          >
            <tr>
              <th className="px-2 py-2 text-left w-12">Pos</th>
              {type === 'drivers' && <th className="px-2 py-2 w-12"></th>}
              <th className="px-2 py-2 text-left">
                {type === 'drivers' ? 'Driver' : 'Constructor'}
              </th>
              {type === 'constructors' && <th className="px-2 py-2 text-center w-12">Logo</th>}
              {hoveredMeeting && <th className="px-2 py-2 text-right w-16"></th>}
              <th className="px-2 py-2 text-right w-16">Pts</th>
            </tr>
          </thead>
        <tbody>
          {standingsWithPointsAdded.map((standing, index) => {
            const entityId = type === 'drivers' ? standing.driver_id : standing.team_id;
            const isSelected = entityId && selectedEntityIds?.has(entityId);
            const isFaded = hasSelections && !isSelected;
            
            return (
            <tr 
              key={entityId}
              className={`border-t border-zinc-900 hover:bg-overlay-50 transition-all cursor-pointer ${
                isSelected ? 'bg-overlay-100' : ''
              } ${isFaded ? 'opacity-40' : ''}`}
              onMouseEnter={() => onHoverEntity?.(entityId || null)}
              onMouseLeave={() => onHoverEntity?.(null)}
              onClick={() => entityId && onToggleEntity?.(entityId)}
            >
              {/* Position */}
              <td className="px-2 py-2 font-mono text-xs text-zinc-500">
                {index + 1}
              </td>

              {/* Team Logo (drivers only - no header) */}
              {type === 'drivers' && (
                <td className="px-2 py-2">
                  {standing.logo_url ? (
                    <img
                      src={standing.logo_url}
                      alt={`${standing.team_name} logo`}
                      className="w-6 h-6 mx-auto object-contain"
                    />
                  ) : (
                    <div 
                      className="w-8 h-8 rounded-sm border border-zinc-800 mx-auto"
                      style={{ backgroundColor: '#18181b' }}
                      title="Logo not available"
                    />
                  )}
                </td>
              )}

              {/* Driver/Constructor Name */}
              <td className="px-2 py-2 text-sm">
                {type === 'drivers' ? (
                  <div className="flex flex-col">
                    <span className="text-white font-extrabold">{standing.driver_name?.split(' ').pop()}</span>
                    <span className="text-zinc-500 font-mono font-bold text-xs">{standing.name_acronym}</span>
                  </div>
                ) : (
                  <span className="text-white">{standing.team_name}</span>
                )}
              </td>

              {/* Team Logo (constructors only - with header) */}
              {type === 'constructors' && (
                <td className="px-2 py-2">
                  {standing.logo_url ? (
                    <img
                      src={standing.logo_url}
                      alt={`${standing.team_name} logo`}
                      className="w-6 h-6 mx-auto object-contain"
                    />
                  ) : (
                    <div 
                      className="w-8 h-8 rounded-sm border border-zinc-800 mx-auto"
                      style={{ backgroundColor: '#18181b' }}
                      title="Logo not available"
                    />
                  )}
                </td>
              )}

              {/* Points Added (only shown when hovering over a meeting) */}
              {hoveredMeeting && (
                <td className="px-2 py-2 font-mono text-xs text-zinc-500 font-medium text-right">
                  +{standing.pointsAdded}
                </td>
              )}

              {/* Cumulative Points */}
              <td className="px-2 py-2 font-mono text-base text-white font-bold text-right">
                {standing.cumulative_points}
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
};
