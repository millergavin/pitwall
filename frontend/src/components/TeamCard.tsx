import { useState } from 'react';

export interface TeamCardData {
  team_id: string;
  team_name: string;
  display_name: string | null;
  color_hex: string;
  logo_url: string | null;
  car_image_url: string | null;
}

interface TeamCardProps {
  team: TeamCardData;
  onClick?: () => void;
}

export const TeamCard = ({ team, onClick }: TeamCardProps) => {
  const [imageError, setImageError] = useState(false);

  // Ensure color_hex has # prefix
  const teamColor = team.color_hex?.startsWith('#') 
    ? team.color_hex 
    : `#${team.color_hex || '666'}`;

  const hasCarImage = team.car_image_url && !imageError;

  return (
    <div
      onClick={onClick}
      className="relative overflow-hidden rounded-corner cursor-pointer group transition-transform hover:scale-[1.02] active:scale-[0.98]"
      style={{
        backgroundColor: teamColor,
        aspectRatio: '16 / 5',
      }}
    >
      {/* Halftone Gradient Overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-40"
        style={{
          backgroundImage: 'url(/assets/textures/halftone.webp)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          mixBlendMode: 'multiply',
        }}
      />

      {/* Content Container */}
      <div className="relative h-full flex flex-col">
        {/* Top section - Team name and logo */}
        <div className="flex justify-between items-start p-6 z-10">
          {/* Team Name */}
          <div>
            <h2
              className="text-white f1-display-bold text-4xl leading-none uppercase"
              style={{
                textShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
              }}
            >
              {team.team_name}
            </h2>
          </div>

          {/* Team Logo Badge - Top right corner, full color on white circle */}
          {team.logo_url && (
            <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center shadow-lg flex-shrink-0">
              <img
                src={team.logo_url}
                alt={`${team.team_name} logo`}
                className="w-10 h-10 object-contain"
              />
            </div>
          )}
        </div>

        {/* Bottom section - Car photo */}
        <div className="flex-1 relative overflow-hidden">
          {hasCarImage && (
            <div className="absolute inset-0 flex items-center justify-start px-6 pb-6">
              <img
                src={team.car_image_url}
                alt={`${team.team_name} car`}
                className="h-full w-[70%] object-contain"
                onError={() => setImageError(true)}
              />
            </div>
          )}
        </div>
      </div>

      {/* Hover effect overlay */}
      <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none" />
    </div>
  );
};
