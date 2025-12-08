import { DriverAvatar } from '../DriverAvatar';

export type DriverImageType = 'team-logo' | 'driver-avatar';
export type DriverNameFormat = 'last-name' | 'full-name';

interface DriverNameCellProps {
  driverName: string;
  nameAcronym: string;
  driverNumber?: number;
  
  // For team logo variant
  teamLogoUrl?: string;
  teamName?: string;
  
  // For driver avatar variant
  headshotUrl?: string | null;
  headshotOverride?: string | null;
  teamColor?: string;
  
  // Control which to show
  imageType?: DriverImageType;
  nameFormat?: DriverNameFormat;
  
  // Secondary line options (mutually exclusive priority order)
  showPoints?: boolean;           // If true, shows points (highest priority)
  points?: number;                // Points value
  deltaFromLeader?: number;       // Delta from leader (shown with points)
  showTeamName?: boolean;         // If true (and !showPoints), shows team name
  showNumber?: boolean;           // Used with acronym if nothing else shown (default: true)
  
  className?: string;
}

export const DriverNameCell = ({
  driverName,
  nameAcronym,
  driverNumber,
  teamLogoUrl,
  teamName,
  headshotUrl,
  headshotOverride,
  teamColor,
  imageType = 'team-logo',
  nameFormat = 'last-name',
  showPoints = false,
  points,
  deltaFromLeader,
  showTeamName = false,
  showNumber = true,
  className = '',
}: DriverNameCellProps) => {
  // Determine what to show on first line
  const displayName = nameFormat === 'full-name' 
    ? driverName 
    : driverName.split(' ').pop() || driverName;

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      {/* Image: Team Logo or Driver Avatar */}
      {imageType === 'team-logo' ? (
        // Team Logo
        teamLogoUrl ? (
          <img
            src={teamLogoUrl}
            alt={`${teamName} logo`}
            className="w-6 h-6 object-contain flex-shrink-0"
          />
        ) : (
          <div className="w-6 h-6 bg-zinc-800 rounded flex-shrink-0" />
        )
      ) : (
        // Driver Avatar
        <DriverAvatar
          driverName={driverName}
          nameAcronym={nameAcronym}
          headshotUrl={headshotUrl}
          headshotOverride={headshotOverride}
          teamColor={teamColor || '666'}
          size="xs"
        />
      )}

      {/* Driver Name and Secondary Info */}
      <div className="flex flex-col">
        {/* First line: Driver name */}
        <span className="text-white font-extrabold text-sm">
          {displayName}
        </span>
        
        {/* Second line: Points OR Team name OR Acronym + Number */}
        {showPoints && points !== undefined ? (
          // Show points + delta
          <span className="text-zinc-500 text-xs f1-display-regular">
            {points} pts
            {deltaFromLeader !== undefined && deltaFromLeader > 0 && (
              <span className="ml-2">(-{deltaFromLeader})</span>
            )}
          </span>
        ) : showTeamName ? (
          // Show team name
          <span className="text-zinc-500 text-xs">
            {teamName}
          </span>
        ) : (
          // Show acronym + number (default)
          <span className="text-zinc-500 font-mono font-bold text-xs">
            {nameAcronym}
            {showNumber && driverNumber && (
              <>
                <span className="inline-block w-3" />
                #{driverNumber}
              </>
            )}
          </span>
        )}
      </div>
    </div>
  );
};

