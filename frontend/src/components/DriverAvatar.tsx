import { useState } from 'react';

type AvatarSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

interface DriverAvatarProps {
  driverName: string;
  nameAcronym: string;
  headshotUrl?: string | null;
  headshotOverride?: string | null;
  teamColor: string;
  size?: AvatarSize;
  className?: string;
}

export const DriverAvatar = ({
  driverName,
  nameAcronym,
  headshotUrl,
  headshotOverride,
  teamColor,
  size = 'md',
  className = '',
}: DriverAvatarProps) => {
  const [imageError, setImageError] = useState(false);

  // Use override if available, otherwise use regular headshot_url
  const imageUrl = headshotOverride || headshotUrl;

  // Ensure color_hex has # prefix
  const bgColor = teamColor?.startsWith('#') ? teamColor : `#${teamColor || '666'}`;

  // Size configurations
  const sizeClasses = {
    xs: 'w-6 h-6', // 24px - favicon/tiny
    sm: 'w-8 h-8', // 32px - small icon
    md: 'w-12 h-12', // 48px - standard icon
    lg: 'w-16 h-16', // 64px - larger icon
    xl: 'w-24 h-24', // 96px - profile/social media size
  };

  const acronymSizes = {
    xs: 'text-[8px]',
    sm: 'text-[10px]',
    md: 'text-sm',
    lg: 'text-lg',
    xl: 'text-2xl',
  };

  return (
    <div
      className={`relative rounded-full overflow-hidden flex-shrink-0 ${sizeClasses[size]} ${className}`}
      style={{ backgroundColor: bgColor }}
    >
      {/* Halftone overlay for texture */}
      <div
        className="absolute inset-0 pointer-events-none opacity-30"
        style={{
          backgroundImage: 'url(/assets/textures/halftone.webp)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          mixBlendMode: 'multiply',
        }}
      />

      {/* Driver image */}
      {imageUrl && !imageError ? (
        <img
          src={imageUrl}
          alt={driverName}
          className="w-full h-full object-cover relative z-10"
          onError={() => setImageError(true)}
        />
      ) : (
        // Fallback to acronym
        <div className="w-full h-full flex items-center justify-center relative z-10">
          <span
            className={`text-white f1-display-bold ${acronymSizes[size]} opacity-90`}
            style={{
              textShadow: '0 1px 2px rgba(0, 0, 0, 0.3)',
            }}
          >
            {nameAcronym}
          </span>
        </div>
      )}

      {/* Subtle border overlay */}
      <div className="absolute inset-0 rounded-full ring-1 ring-inset ring-white ring-opacity-10 pointer-events-none" />
    </div>
  );
};

