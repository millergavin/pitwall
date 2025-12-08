import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export interface ChampionshipTeamData {
  team_id: string;
  team_name: string;
  display_name?: string;
  color_hex: string;
  logo_url?: string | null;
  cumulative_points: number;
}

interface ChampionshipTeamRowProps {
  position: number;
  team: ChampionshipTeamData;
}

export const ChampionshipTeamRow = ({ position, team }: ChampionshipTeamRowProps) => {
  const navigate = useNavigate();
  const [imageError, setImageError] = useState(false);

  // Ensure color_hex has # prefix
  const teamColor = team.color_hex?.startsWith('#') 
    ? team.color_hex 
    : `#${team.color_hex || '666'}`;

  const displayName = team.display_name || team.team_name;

  const handleNameClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/teams/${team.team_id}`);
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

        {/* Team Logo Container - fixed width for alignment (same as driver image) */}
        <div 
          className="flex-shrink-0 h-full flex items-center justify-center"
          style={{ width: '72px' }}
        >
          {team.logo_url && !imageError ? (
            <div className="w-12 h-12 rounded-full bg-black/90 flex items-center justify-center backdrop-blur-lg">
              <img
                src={team.logo_url}
                alt={team.team_name}
                className="w-8 h-8 object-contain"
                onError={() => setImageError(true)}
              />
            </div>
          ) : (
            <div className="w-12 h-12 rounded-full bg-black/30 flex items-center justify-center">
              <span className="text-white/60 f1-display-bold text-sm">
                {team.team_name?.charAt(0)}
              </span>
            </div>
          )}
        </div>

        {/* Team Name - clickable to team details */}
        <div 
          className="flex-1 flex items-center px-4 cursor-pointer"
          onClick={handleNameClick}
        >
          <span 
            className="text-white f1-display-bold text-xl transition-opacity duration-150 hover:opacity-70"
            style={{ textShadow: '0 2px 4px rgba(0, 0, 0, 0.4)' }}
          >
            {displayName}
          </span>
        </div>

        {/* Points */}
        <div 
          className="flex-shrink-0 px-6 f1-display-bold text-white text-xl italic"
          style={{ textShadow: '0 2px 4px rgba(0, 0, 0, 0.4)' }}
        >
          {team.cumulative_points} pts
        </div>
      </div>

    </div>
  );
};

