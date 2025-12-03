import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';

interface NavMenuItemProps {
  to: string;
  children: ReactNode;
}

export const NavMenuItem = ({ to, children }: NavMenuItemProps) => {
  const location = useLocation();
  const isActive = location.pathname === to;

  return (
    <Link to={to} className="block">
      <motion.div
        className={`
          text-base font-medium px-3 py-2 rounded-corner
          transition-colors duration-150
          ${isActive 
            ? 'bg-overlay-100 text-white' 
            : 'bg-transparent text-zinc-500 hover:bg-overlay-50'
          }
        `}
        whileHover={{ x: 4 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
      >
        {children}
      </motion.div>
    </Link>
  );
};

