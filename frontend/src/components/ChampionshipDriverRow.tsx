import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export interface ChampionshipDriverData {
  driver_id: string;
  driver_name: string;
  first_name?: string;
  last_name?: string;
  name_acronym?: string;
  headshot_url?: string | null;
  headshot_override?: string | null;
  team_id?: string;
  color_hex: string;
  cumulative_points: number;
}

interface ChampionshipDriverRowProps {
  position: number;
  driver: ChampionshipDriverData;
}

export const ChampionshipDriverRow = ({ position, driver }: ChampionshipDriverRowProps) => {
  const navigate = useNavigate();
  const [imageError, setImageError] = useState(false);

  const headshotUrl = driver.headshot_override || driver.headshot_url;
  
  // Ensure color_hex has # prefix
  const teamColor = driver.color_hex?.startsWith('#') 
    ? driver.color_hex 
    : `#${driver.color_hex || '666'}`;

  // Parse name - use first_name/last_name if available, otherwise split driver_name
  const firstName = driver.first_name || driver.driver_name?.split(' ')[0] || '';
  const lastName = driver.last_name || driver.driver_name?.split(' ').slice(1).join(' ') || '';

  const handleNameClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/drivers/${driver.driver_id}`);
  };

  return (
    <div
      className="relative overflow-hidden rounded-corner"
      style={{
        backgroundColor: teamColor,
        height: '80px',
      }}
    >
      {/* Halftone Gradient Overlay - flipped horizontally */}
      <div
        className="absolute inset-0 pointer-events-none opacity-50"
        style={{
          backgroundImage: 'url(/assets/textures/halftone.webp)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          mixBlendMode: 'multiply',
          transform: 'scaleX(-1)',
        }}
      />

      {/* Content Container */}
      <div className="relative h-full flex items-center">
        {/* Position Number - fixed width, centered */}
        <div 
          className="flex-shrink-0 flex items-center justify-center f1-display-bold text-white text-2xl"
          style={{ 
            width: '56px',
            textShadow: '0 2px 4px rgba(0, 0, 0, 0.4)',
          }}
        >
          {position}
        </div>

        {/* Driver Image Container - fixed width for alignment */}
        <div 
          className="flex-shrink-0 h-full overflow-hidden"
          style={{ width: '72px' }}
        >
          {headshotUrl && !imageError ? (
            <img
              src={headshotUrl}
              alt={driver.driver_name}
              className="h-full w-full object-cover object-top"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-black/20">
              <span className="text-white/40 f1-display-bold text-lg">
                {driver.name_acronym || firstName.charAt(0)}
              </span>
            </div>
          )}
        </div>

        {/* Driver Name - clickable to driver details */}
        <div 
          className="flex-1 flex items-center gap-2 px-4 cursor-pointer group/name"
          onClick={handleNameClick}
        >
          <span 
            className="text-white f1-display-regular text-xl transition-opacity duration-150 group-hover/name:opacity-60"
            style={{ textShadow: '0 2px 4px rgba(0, 0, 0, 0.4)' }}
          >
            {firstName}
          </span>
          <span 
            className="text-white f1-display-bold text-xl transition-opacity duration-150 group-hover/name:opacity-60"
            style={{ textShadow: '0 2px 4px rgba(0, 0, 0, 0.4)' }}
          >
            {lastName}
          </span>
        </div>

        {/* Points */}
        <div 
          className="flex-shrink-0 px-6 f1-display-bold text-white text-xl italic"
          style={{ textShadow: '0 2px 4px rgba(0, 0, 0, 0.4)' }}
        >
          {driver.cumulative_points} pts
        </div>
      </div>

    </div>
  );
};

