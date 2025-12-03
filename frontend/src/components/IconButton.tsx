import type { ButtonHTMLAttributes } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import type { IconDefinition } from '@fortawesome/fontawesome-svg-core';

type IconButtonSize = 'sm' | 'md' | 'lg';
type IconButtonVariant = 'primary' | 'secondary' | 'text' | 'outline' | 'destructive';

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  size?: IconButtonSize;
  variant?: IconButtonVariant;
  icon: IconDefinition;
  'aria-label': string; // Required for accessibility
  iconClassName?: string; // Optional className for the icon itself
}

export const IconButton = ({
  size = 'md',
  variant = 'primary',
  icon,
  className = '',
  iconClassName = '',
  disabled,
  'aria-label': ariaLabel,
  ...props
}: IconButtonProps) => {
  // Size-based classes - proper square buttons with fixed dimensions
  const sizeClasses = {
    sm: 'w-8 h-8',    // 32px square
    md: 'w-10 h-10',  // 40px square
    lg: 'w-12 h-12',  // 48px square
  };

  // Icon sizes
  const iconSizes = {
    sm: 'text-sm',   // 14px
    md: 'text-base', // 16px
    lg: 'text-lg',   // 18px
  };

  // Variant-based classes with faint white overlay on hover
  const variantClasses = {
    primary: 'bg-f1-red text-white hover:bg-[#981b1b]',
    secondary: 'bg-zinc-950 border border-zinc-900 text-white hover:bg-zinc-900',
    text: 'bg-transparent text-white hover:bg-red-500',
    outline: 'bg-transparent border border-zinc-600 text-white hover:bg-red-500 hover:border-white',
    destructive: 'bg-transparent border border-f1-bright-red text-f1-bright-red hover:bg-f1-red hover:text-black',
  };

  const baseClasses = `
    inline-flex items-center justify-center
    rounded-corner
    transition-colors duration-150
    disabled:opacity-50 disabled:cursor-not-allowed
    focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-0
    ${sizeClasses[size]}
    ${variantClasses[variant]}
    ${className}
  `.trim().replace(/\s+/g, ' ');

  const iconClasses = `${iconSizes[size]} ${iconClassName}`.trim();

  return (
    <button
      className={baseClasses}
      disabled={disabled}
      aria-label={ariaLabel}
      {...props}
    >
      <FontAwesomeIcon icon={icon} className={iconClasses} />
    </button>
  );
};

