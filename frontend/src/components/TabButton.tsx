import type { ButtonHTMLAttributes, ReactNode } from 'react';

type TabButtonSize = 'sm' | 'md' | 'lg';

interface TabButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  size?: TabButtonSize;
  active?: boolean;
  children: ReactNode;
}

export const TabButton = ({
  size = 'md',
  active = false,
  children,
  className = '',
  disabled,
  ...props
}: TabButtonProps) => {
  // Size-based classes with inline padding override
  const sizeStyles = {
    sm: { paddingLeft: '8px', paddingRight: '8px', paddingTop: '4px', paddingBottom: '4px' },
    md: { paddingLeft: '12px', paddingRight: '12px', paddingTop: '8px', paddingBottom: '8px' },
    lg: { paddingLeft: '16px', paddingRight: '16px', paddingTop: '10px', paddingBottom: '10px' },
  };

  const textSizeClasses = {
    sm: 'button-sm',
    md: 'button-md',
    lg: 'button-lg',
  };

  // Active/inactive state classes
  const stateClasses = active
    ? 'bg-f1-red text-white hover:bg-[#981b1b]'
    : 'bg-zinc-950 border border-zinc-900 hover:bg-zinc-900 hover:text-white';
  
  // Inactive text color via inline style (more reliable than Tailwind class)
  const textColorStyle = !active ? { color: '#71717a' } : undefined;

  const baseClasses = `
    inline-flex items-center justify-center gap-2
    rounded-corner
    transition-colors duration-150
    disabled:opacity-50 disabled:cursor-not-allowed
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-0
    ${textSizeClasses[size]}
    ${stateClasses}
    ${className}
  `.trim().replace(/\s+/g, ' ');

  return (
    <button
      className={baseClasses}
      style={{ ...sizeStyles[size], ...textColorStyle }}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};

