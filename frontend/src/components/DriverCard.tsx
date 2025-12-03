import { useState } from 'react';

export interface DriverCardData {
  driver_id: string;
  driver_number: number;
  first_name: string;
  last_name: string;
  full_name: string;
  name_acronym: string;
  headshot_url: string | null;
  headshot_override: string | null;
  team_id: string;
  team_name: string;
  color_hex: string;
  team_logo_url: string | null;
}

interface DriverCardProps {
  driver: DriverCardData;
  onClick?: () => void;
}

export const DriverCard = ({ driver, onClick }: DriverCardProps) => {
  const [imageError, setImageError] = useState(false);

  // Use override if available, otherwise use regular headshot_url
  const headshotUrl = driver.headshot_override || driver.headshot_url;

  // Ensure color_hex has # prefix
  const teamColor = driver.color_hex?.startsWith('#') 
    ? driver.color_hex 
    : `#${driver.color_hex || '666'}`;

  // Helper to convert first letter to uppercase, rest lowercase
  const toTitleCase = (str: string) => {
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  };

  return (
    <div
      onClick={onClick}
      className="relative overflow-hidden rounded-corner cursor-pointer group transition-transform hover:scale-[1.02] active:scale-[0.98]"
      style={{
        backgroundColor: teamColor,
        aspectRatio: '16 / 9',
      }}
    >
      {/* Halftone Gradient Overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-50"
        style={{
          backgroundImage: 'url(/assets/textures/halftone.webp)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          mixBlendMode: 'multiply',
        }}
      />

      {/* Driver Number - Large background graphic */}
      <div className="absolute inset-0 flex items-center justify-start pl-6">
        <span
          className="text-[160px] leading-none f1-display-bold text-black opacity-15 select-none"
          style={{ 
            fontVariantNumeric: 'tabular-nums',
            letterSpacing: '-0.07em'
          }}
        >
          {driver.driver_number}
        </span>
      </div>

      {/* Content Container */}
      <div className="relative h-full flex">
        {/* Left side - Driver info */}
        <div className="flex-1 flex flex-col justify-between p-6">
          {/* Driver Name */}
          <div className="z-10">
            <h3
              className="text-white f1-display-regular text-3xl leading-none mb-1"
              style={{
                textShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
              }}
            >
              {toTitleCase(driver.first_name)}
            </h3>
            <h2
              className="text-white f1-display-bold text-4xl leading-none"
              style={{
                textShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
              }}
            >
              {toTitleCase(driver.last_name)}
            </h2>
          </div>

          {/* Team Logo Badge - Bottom left corner */}
          {driver.team_logo_url && (
            <div className="relative w-10 h-10 rounded-full bg-black bg-opacity-50 flex items-center justify-center backdrop-blur-sm">
              <img
                src={driver.team_logo_url}
                alt={`${driver.team_name} logo`}
                className="w-6 h-6 object-contain opacity-90"
                style={{ filter: 'brightness(0) invert(1)' }} // Make logo white
              />
            </div>
          )}
        </div>

        {/* Right side - Driver photo */}
        <div className="relative flex-shrink-0" style={{ width: '50%' }}>
          {/* Photo container - 3:4 aspect ratio, top-aligned, bottom cuts off */}
          <div className="absolute top-0 right-0 h-full w-full overflow-hidden">
            {headshotUrl && !imageError ? (
              <img
                src={headshotUrl}
                alt={driver.full_name}
                className="absolute top-0 left-0 w-full h-auto min-h-full object-cover"
                onError={() => setImageError(true)}
                style={{
                  objectPosition: 'center top',
                }}
              />
            ) : (
              <div className="w-full h-full bg-zinc-800 bg-opacity-20 flex items-center justify-center">
                <span className="text-white text-6xl opacity-20 f1-display-bold">
                  {driver.name_acronym}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Hover effect overlay */}
      <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none" />
    </div>
  );
};
