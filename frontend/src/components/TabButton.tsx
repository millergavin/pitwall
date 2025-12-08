import type { ButtonHTMLAttributes, ReactNode } from 'react';

type TabButtonSize = 'sm' | 'md' | 'lg';
type TabButtonVariant = 'default' | 'ghost';

interface TabButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  size?: TabButtonSize;
  variant?: TabButtonVariant;
  active?: boolean;
  children: ReactNode;
}

export const TabButton = ({
  size = 'md',
  variant = 'default',
  active = false,
  children,
  className = '',
  disabled,
  ...props
}: TabButtonProps) => {
  const sizeClasses = {
    sm: 'px-2 py-1 button-sm',
    md: 'px-3 py-2 button-md',
    lg: 'px-4 py-2.5 button-lg',
  };

  // Active/inactive state classes based on variant
  const getStateClasses = () => {
    if (variant === 'ghost') {
      return active
        ? 'bg-black text-white border border-zinc-700'
        : 'bg-transparent text-zinc-700 hover:bg-zinc-900 hover:text-zinc-200';
    }
    
    // Default variant
    return active
      ? 'bg-f1-red text-white hover:bg-[#981b1b]'
      : 'bg-transparent text-zinc-500 hover:bg-zinc-900 hover:text-white';
  };

  const stateClasses = getStateClasses();

  const baseClasses = `
    inline-flex items-center justify-center gap-2
    rounded-corner
    transition-colors duration-150
    disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none
    focus-visible:outline-none focus-visible:ring-offset-bg-0
    ${sizeClasses[size]}
    ${stateClasses}
    ${className}
  `.trim().replace(/\s+/g, ' ');

  return (
    <button
      className={baseClasses}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};

