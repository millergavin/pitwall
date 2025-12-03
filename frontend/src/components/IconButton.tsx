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
  // Size-based classes - square buttons (24x24, 32x32, 40x40)
  // Padding calculated to achieve exact square dimensions
  const sizeClasses = {
    sm: 'p-[6px]', // 24px square (6px + 12px icon + 6px)
    md: 'p-[9px]', // 32px square (9px + 14px icon + 9px)
    lg: 'p-[12px]', // 40px square (12px + 16px icon + 12px)
  };

  // Icon sizes matching button text sizes
  const iconSizes = {
    sm: 'text-[12px]',
    md: 'text-[14px]',
    lg: 'text-[16px]',
  };

  // Variant-based classes (same as Button)
  const variantClasses = {
    primary: 'bg-f1-red text-white hover:bg-[#981b1b]',
    secondary: 'bg-zinc-950 border border-zinc-900 text-white hover:bg-zinc-900',
    text: 'bg-transparent text-white hover:bg-overlay-100',
    outline: 'bg-transparent border border-zinc-600 text-white hover:bg-overlay-500 hover:border-white',
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

