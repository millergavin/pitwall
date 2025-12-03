import type { ReactNode } from 'react';
import { GlobalHeader } from './GlobalHeader';
import { useStore } from '../store/useStore';

interface PageLayoutProps {
  children: ReactNode;
  pageTitle?: string;
  sidebar?: ReactNode;
}

export const PageLayout = ({ children, pageTitle, sidebar }: PageLayoutProps) => {
  const { sidebarOpen, sidebarWidth } = useStore();

  return (
    <div className="h-screen bg-0 flex flex-col">
      <GlobalHeader pageTitle={pageTitle} />
      
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - Fixed position, independent scroll */}
        {sidebar && (
          <aside
            className="bg-1 transition-all duration-200 overflow-hidden flex-shrink-0"
            style={{
              width: sidebarOpen ? `${sidebarWidth}px` : '0px',
            }}
          >
            <div
              className="h-full overflow-y-auto"
              style={{
                width: `${sidebarWidth}px`,
                opacity: sidebarOpen ? 1 : 0,
                transition: 'opacity 0.2s',
              }}
            >
              {sidebar}
            </div>
          </aside>
        )}

        {/* Main Content - Independent scroll */}
        <main className="flex-1 flex flex-col min-h-0">
          <div className="p-6 flex-1 flex flex-col min-h-0">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

