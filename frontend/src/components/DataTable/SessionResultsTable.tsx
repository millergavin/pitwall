import { FontAwesomeIcon } from '../../lib/fontawesome';
import { faStopwatch, faChevronUp, faChevronDown } from '@fortawesome/free-solid-svg-icons';
import { 
  Table, 
  TableHeader, 
  TableHeaderCell, 
  TableBody, 
  TableRow, 
  TableCell,
  DriverNameCell,
  PositionCell,
} from '../Table';
import type { DriverImageType } from '../Table';

interface SessionResult {
  driver_id: string;
  driver_number: number;
  driver_name: string;
  name_acronym: string;
  team_name: string;
  team_logo_url?: string;
  team_color?: string;
  headshot_url?: string | null;
  headshot_override?: string | null;
  grid_position?: number | null;
  finish_position?: number | null;
  position?: number; // For qualifying/practice
  duration_ms?: number | null;
  gap_to_leader_ms?: number | null;
  best_lap_ms?: number | null;
  quali_lap_ms?: number | null;
  time?: string; // Formatted time string
  gap?: string; // Formatted gap string
  laps?: number;
  points?: number | null;
  status?: string;
  fastest_lap?: boolean;
}

interface SessionResultsTableProps {
  results: SessionResult[];
  sessionType: 'race' | 'qualifying' | 'practice' | 'sprint';
  onDriverClick?: (driverId: string) => void;
  showPositionChange?: boolean;
  showPoints?: boolean;
  showLaps?: boolean;
  showFastestLap?: boolean;
  title?: string;
  driverImageType?: DriverImageType;
}

export const SessionResultsTable = ({
  results,
  sessionType,
  onDriverClick,
  showPositionChange = true,
  showPoints = true,
  showLaps = false,
  showFastestLap = true,
  title,
  driverImageType,
}: SessionResultsTableProps) => {
  const isRaceSession = sessionType === 'race' || sessionType === 'sprint';
  const isQualifying = sessionType === 'qualifying' || sessionType === 'practice';
  
  // Default to driver avatar for all session types
  const effectiveImageType = driverImageType || 'driver-avatar';

  const formatDuration = (ms: number | null | undefined) => {
    if (ms === null || ms === undefined) return '-';
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const milliseconds = ms % 1000;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
  };

  const formatLapTime = (ms: number | null | undefined) => {
    if (ms === null || ms === undefined) return '-';
    const totalSeconds = ms / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toFixed(3).padStart(6, '0')}`;
  };

  const formatGap = (gapMs: number | null | undefined) => {
    if (gapMs === null || gapMs === undefined) return '-';
    const totalSeconds = gapMs / 1000;
    return `+${totalSeconds.toFixed(3)}s`;
  };
  
  // For qualifying, calculate gap based on quali_lap_ms
  const getQualifyingGap = (result: SessionResult, leaderLapMs: number | null) => {
    if (!result.quali_lap_ms || !leaderLapMs) return '-';
    const gapMs = result.quali_lap_ms - leaderLapMs;
    return `+${(gapMs / 1000).toFixed(3)}s`;
  };
  
  // Get the leader's lap time for gap calculations
  const leaderLapMs = isQualifying && results.length > 0 
    ? (results[0].quali_lap_ms ?? results[0].best_lap_ms ?? null)
    : null;

  return (
    <div>
      {/* Table Title */}
      {title && (
        <div className="mb-4">
          <h2 className="text-white f1-display-bold text-xl">{title}</h2>
        </div>
      )}

      {/* Table */}
      <Table>
        <TableHeader sticky>
          <tr>
            <TableHeaderCell width="4rem"></TableHeaderCell>
            <TableHeaderCell width="18rem">Driver</TableHeaderCell>
            <TableHeaderCell align="left" width="18rem"></TableHeaderCell>
            <TableHeaderCell width="16rem">Team</TableHeaderCell>
            <TableHeaderCell align="right" width="16rem">Time</TableHeaderCell>
            <TableHeaderCell align="right" width="20rem">Gap</TableHeaderCell>
            {showLaps && <TableHeaderCell align="right" width="12rem">Laps</TableHeaderCell>}
            <TableHeaderCell align="right">Pts</TableHeaderCell>
          </tr>
        </TableHeader>
        <TableBody>
          {results.map((result, index) => {
            const position = result.finish_position || result.position || index + 1;
            const positionChange = result.grid_position && result.finish_position
              ? result.grid_position - result.finish_position
              : null;

            return (
              <TableRow
                key={result.driver_id}
                onClick={() => onDriverClick?.(result.driver_id)}
                hoverable={!!onDriverClick}
              >
                {/* Position */}
                <PositionCell position={position} />

                {/* Driver Name with Avatar */}
                <TableCell>
                  <div className="flex items-top gap-3">
                    <DriverNameCell
                      driverName={result.driver_name}
                      nameAcronym={result.name_acronym}
                      driverNumber={result.driver_number}
                      teamLogoUrl={result.team_logo_url}
                      teamName={result.team_name}
                      headshotUrl={result.headshot_url}
                      headshotOverride={result.headshot_override}
                      teamColor={result.team_color}
                      imageType={effectiveImageType}
                      nameFormat="full-name"
                    />
                    
                    {result.fastest_lap && showFastestLap && (
                      <div className="w-5 h-5 bg-purple-600 rounded flex items-center justify-center flex-shrink-0">
                        <FontAwesomeIcon icon={faStopwatch} className="text-white text-xs" />
                      </div>
                    )}
                  </div>
                </TableCell>

                {/* Position Change - Always present for alignment, but only shows data for Race/Sprint */}
                <TableCell align="left">
                  {showPositionChange && isRaceSession && positionChange !== null && positionChange !== 0 ? (
                    <div className="flex items-center justify-left gap-1">
                      <FontAwesomeIcon 
                        icon={positionChange > 0 ? faChevronUp : faChevronDown} 
                        className={`text-xs ${positionChange > 0 ? 'text-green-400' : 'text-red-400'}`}
                      />
                      <span className={`text-xs font-bold ${positionChange > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {Math.abs(positionChange)}
                      </span>
                    </div>
                  ) : isRaceSession ? (
                    <span className="text-zinc-600">-</span>
                  ) : (
                    <span>&nbsp;</span>
                  )}
                </TableCell>

                {/* Team Name with Logo */}
                <TableCell>
                  <div className="flex items-center gap-3">
                    {result.team_logo_url && (
                      <img 
                        src={result.team_logo_url} 
                        alt={result.team_name}
                        className="w-5 h-5 object-contain flex-shrink-0"
                      />
                    )}
                    <span className="text-zinc-400">{result.team_name}</span>
                  </div>
                </TableCell>

                {/* Time */}
                <TableCell align="right" mono size="sm">
                  {(() => {
                    // For qualifying/practice: show quali_lap_ms or best_lap_ms (no status)
                    if (isQualifying) {
                      const lapTime = result.quali_lap_ms || result.best_lap_ms;
                      return lapTime ? formatLapTime(lapTime) : '-';
                    }
                    
                    // For race/sprint: show status for DNF/DSQ/DNS, otherwise show duration
                    if (result.status && ['dnf', 'dsq', 'dns'].includes(result.status.toLowerCase())) {
                      return (
                        <span className="text-zinc-500 uppercase text-xs">
                          {result.status.toUpperCase()}
                        </span>
                      );
                    }
                    
                    return result.time || (result.duration_ms !== null && result.duration_ms !== undefined 
                      ? (index === 0 ? formatDuration(result.duration_ms) : result.gap)
                      : '-'
                    );
                  })()}
                </TableCell>

                {/* Gap */}
                <TableCell align="right" mono size="sm" color="zinc-500">
                  {(() => {
                    // Leader or DNF/DSQ/DNS: show dash
                    if (index === 0 || (result.status && ['dnf', 'dsq', 'dns'].includes(result.status.toLowerCase()))) {
                      return '-';
                    }
                    
                    // For qualifying/practice: calculate gap from quali_lap_ms
                    if (isQualifying) {
                      return getQualifyingGap(result, leaderLapMs);
                    }
                    
                    // For race/sprint: use gap_to_leader_ms
                    return result.gap || formatGap(result.gap_to_leader_ms);
                  })()}
                </TableCell>

                {/* Laps */}
                {showLaps && (
                  <TableCell align="right" mono size="sm" color="zinc-500">
                    {result.laps || '-'}
                  </TableCell>
                )}

                {/* Points - Always present for alignment, only shows values for Race/Sprint */}
                <TableCell align="right" mono size="sm" bold>
                  {showPoints && isRaceSession ? (
                    result.points !== null && result.points !== undefined && result.points > 0 
                      ? `+${result.points}`
                      : <span className="text-zinc-600">+0</span>
                  ) : (
                    <span>&nbsp;</span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
};

