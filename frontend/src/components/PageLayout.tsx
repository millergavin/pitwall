import { useEffect, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { GlobalHeader } from './GlobalHeader';
import { useStore } from '../store/useStore';

interface PageLayoutProps {
  children: ReactNode;
  pageTitle?: string;
  sidebar?: ReactNode;
}

export const PageLayout = ({ children, pageTitle, sidebar }: PageLayoutProps) => {
  const { sidebarOpen, sidebarWidth } = useStore();

  // Update document title when pageTitle changes
  useEffect(() => {
    document.title = pageTitle ? `${pageTitle} / PITWALL` : 'PITWALL';
  }, [pageTitle]);

  return (
    <div className="h-screen bg-0 flex flex-col">
      <GlobalHeader pageTitle={pageTitle} />
      
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - Fixed position, independent scroll */}
        {sidebar && (
          <motion.aside
            className="bg-1 overflow-hidden flex-shrink-0"
            initial={false}
            animate={{
              width: sidebarOpen ? sidebarWidth : 0,
            }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 30,
            }}
          >
            <motion.div
              className="h-full overflow-y-auto"
              style={{ width: sidebarWidth }}
              initial={false}
              animate={{
                opacity: sidebarOpen ? 1 : 0,
              }}
              transition={{
                duration: 0.2,
              }}
            >
              {sidebar}
            </motion.div>
          </motion.aside>
        )}

        {/* Main Content - Independent scroll with fade in */}
        <motion.main 
          className="flex-1 flex flex-col min-h-0"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          <div className="p-6 flex-1 flex flex-col min-h-0">
            {children}
          </div>
        </motion.main>
      </div>
    </div>
  );
};

