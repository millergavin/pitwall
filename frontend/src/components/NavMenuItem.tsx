import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface NavMenuItemProps {
  to: string;
  children: ReactNode;
}

export const NavMenuItem = ({ to, children }: NavMenuItemProps) => {
  const location = useLocation();
  const isActive = location.pathname === to;

  return (
    <Link
      to={to}
      className={`
        block text-base font-medium px-3 py-2 rounded-corner
        transition-colors duration-150
        no-underline
        ${isActive 
          ? 'bg-overlay-100 text-white' 
          : 'bg-transparent text-zinc-600 hover:bg-overlay-50'
        }
      `}
    >
      {children}
    </Link>
  );
};

