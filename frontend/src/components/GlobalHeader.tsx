import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '../store/useStore';
import { IconButton } from './IconButton';
import { DatabaseUpdateIndicator } from './DatabaseUpdateIndicator';
import { Changelog } from './Changelog';
import { faBars, faDatabase, faClockRotateLeft, faShapes } from '@fortawesome/free-solid-svg-icons';

interface GlobalHeaderProps {
  pageTitle?: string;
}

export const GlobalHeader = ({ pageTitle = 'Page Title' }: GlobalHeaderProps) => {
  const { sidebarOpen, setSidebarOpen, sidebarWidth } = useStore();
  const [changelogOpen, setChangelogOpen] = useState(false);

  return (
    <header className="bg-1 pt-2 pb-1 flex items-center w-full flex-shrink-0">
      {/* Left: Sidebar toggle + Logo */}
      <div
        className="flex items-center"
        style={{ width: `${sidebarWidth}px` }}
      >
        <div className="flex items-center gap-2 px-4 py-1">
          <IconButton
            size="md"
            variant="text"
            icon={faBars}
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle sidebar"
          />
          <a
            href="/"
            className="flex items-center px-2 hover:opacity-70 transition-opacity"
            aria-label="Home"
            onClick={(e) => {
              e.preventDefault();
              // Navigate to home/dashboard
              window.location.href = '/';
            }}
          >
            <img
              src="/assets/logo/pitwall_logo-white.svg"
              alt="Pitwall"
              className="h-[14px]"
            />
          </a>
        </div>
      </div>

      {/* Center: Page Title */}
      <div className="flex-1 flex items-center px-6">
        <h1 className="page-title">{pageTitle}</h1>
      </div>

      {/* Right: Action buttons */}
      <div className="flex items-center gap-2 px-6">
        <DatabaseUpdateIndicator />
        <IconButton
          size="md"
          variant="text"
          icon={faClockRotateLeft}
          onClick={() => setChangelogOpen(true)}
          aria-label="Changelog"
          title="Changelog"
        />
        <Link to="/playground" title="Design System Playground">
          <IconButton
            size="md"
            variant="text"
            icon={faShapes}
            aria-label="Design System Playground"
          />
        </Link>
        <Link to="/admin" title="Database Admin">
          <IconButton
            size="md"
            variant="text"
            icon={faDatabase}
            aria-label="Database Admin"
          />
        </Link>
      </div>

      {/* Changelog Panel */}
      <Changelog isOpen={changelogOpen} onClose={() => setChangelogOpen(false)} />
    </header>
  );
};

