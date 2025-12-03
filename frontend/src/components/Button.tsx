import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import type { IconDefinition } from '@fortawesome/fontawesome-svg-core';

type ButtonSize = 'sm' | 'md' | 'lg';
type ButtonVariant = 'primary' | 'secondary' | 'text' | 'outline' | 'destructive';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  size?: ButtonSize;
  variant?: ButtonVariant;
  children: ReactNode;
  icon?: IconDefinition;
  iconPosition?: 'left' | 'right';
}

export const Button = ({
  size = 'md',
  variant = 'primary',
  children,
  icon,
  iconPosition = 'left',
  className = '',
  disabled,
  ...props
}: ButtonProps) => {
  // Size-based classes
  const sizeClasses = {
    sm: 'px-[10px] py-[4px] button-sm', // 24px height (4px top + 16px line-height + 4px bottom)
    md: 'px-[16px] py-[8px] button-md', // 32px height (8px top + 16px line-height + 8px bottom)
    lg: 'px-[20px] py-[10px] button-lg', // 40px height (10px top + 20px line-height + 10px bottom)
  };

  // Variant-based classes
  const variantClasses = {
    primary: 'bg-f1-red text-white hover:bg-[#981b1b]',
    secondary: 'bg-zinc-950 border border-zinc-900 text-white hover:bg-zinc-900',
    text: 'bg-transparent text-white hover:bg-overlay-100',
    outline: 'bg-transparent border border-zinc-600 text-white hover:bg-overlay-100 hover:border-white',
    destructive: 'bg-transparent border border-f1-bright-red text-f1-bright-red hover:bg-f1-red hover:text-black',
  };

  const baseClasses = `
    inline-flex items-center justify-center gap-2
    rounded-corner
    transition-colors duration-150
    disabled:opacity-50 disabled:cursor-not-allowed
    focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-0
    ${sizeClasses[size]}
    ${variantClasses[variant]}
    ${className}
  `.trim().replace(/\s+/g, ' ');

  const iconElement = icon ? (
    <FontAwesomeIcon icon={icon} className={size === 'sm' ? 'text-[12px]' : size === 'md' ? 'text-[14px]' : 'text-[16px]'} />
  ) : null;

  return (
    <button
      className={baseClasses}
      disabled={disabled}
      {...props}
    >
      {icon && iconPosition === 'left' && iconElement}
      {children}
      {icon && iconPosition === 'right' && iconElement}
    </button>
  );
};

