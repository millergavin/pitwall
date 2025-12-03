import { Link } from 'react-router-dom';
import { useStore } from '../store/useStore';
import { IconButton } from './IconButton';
import { ApiStatusIndicator } from './ApiStatusIndicator';
import { DatabaseUpdateIndicator } from './DatabaseUpdateIndicator';
import { faBars, faDatabase, faUser } from '@fortawesome/free-solid-svg-icons';

interface GlobalHeaderProps {
  pageTitle?: string;
}

export const GlobalHeader = ({ pageTitle = 'Page Title' }: GlobalHeaderProps) => {
  const { sidebarOpen, setSidebarOpen, sidebarWidth } = useStore();

  return (
    <header className="bg-1 py-3 flex items-center w-full flex-shrink-0">
      {/* Left: Sidebar toggle + Logo */}
      <div
        className="flex items-center"
        style={{ width: `${sidebarWidth}px` }}
      >
        <div className="flex items-center gap-2 px-8 py-1">
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

      {/* Right: Action buttons + API status */}
      <div className="flex items-center gap-2 px-6">
        <DatabaseUpdateIndicator />
        <Link to="/admin" title="Database Admin">
          <IconButton
            size="md"
            variant="text"
            icon={faDatabase}
            aria-label="Database Admin"
          />
        </Link>
        <IconButton
          size="md"
          variant="text"
          icon={faUser}
          aria-label="User menu"
        />
        <ApiStatusIndicator status="connected" />
      </div>
    </header>
  );
};

