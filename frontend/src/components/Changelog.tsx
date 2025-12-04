import { useState, useEffect } from 'react';

interface Commit {
  hash: string;
  date: string;
  message: string;
  author: string;
}

interface ChangelogData {
  generated: string;
  commits: Commit[];
}

interface ChangelogProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Changelog = ({ isOpen, onClose }: ChangelogProps) => {
  const [changelog, setChangelog] = useState<ChangelogData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen && !changelog) {
      fetch('/changelog.json')
        .then(res => res.json())
        .then(data => {
          setChangelog(data);
          setLoading(false);
        })
        .catch(() => {
          setLoading(false);
        });
    }
  }, [isOpen, changelog]);

  if (!isOpen) return null;

  // Group commits by date
  const groupedByDate = changelog?.commits.reduce((acc, commit) => {
    if (!acc[commit.date]) {
      acc[commit.date] = [];
    }
    acc[commit.date].push(commit);
    return acc;
  }, {} as Record<string, Commit[]>) || {};

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (dateStr === today.toISOString().split('T')[0]) {
      return 'Today';
    }
    if (dateStr === yesterday.toISOString().split('T')[0]) {
      return 'Yesterday';
    }
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
    });
  };

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />
      
      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-96 bg-zinc-950 border-l border-zinc-800 z-50 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <h2 className="text-white f1-display-bold text-lg">Changelog</h2>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white transition-colors rounded-lg hover:bg-zinc-800"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-f1-red border-t-transparent rounded-full animate-spin" />
            </div>
          ) : !changelog ? (
            <div className="text-center py-8 text-zinc-500">
              No changelog available
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(groupedByDate).map(([date, commits]) => (
                <div key={date}>
                  <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3 f1-display-regular">
                    {formatDate(date)}
                  </div>
                  <div className="space-y-2">
                    {commits.map((commit) => (
                      <div
                        key={commit.hash}
                        className="p-3 bg-zinc-900 rounded-lg border border-zinc-800 hover:border-zinc-700 transition-colors"
                      >
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5">
                            <div className="w-2 h-2 rounded-full bg-f1-red" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-white text-sm leading-relaxed">
                              {commit.message}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <code className="text-xs text-zinc-600 font-mono">
                                {commit.hash}
                              </code>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {changelog && (
          <div className="p-4 border-t border-zinc-800">
            <a
              href="https://github.com/millergavin/pitwall/commits/main"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              View all commits on GitHub
            </a>
          </div>
        )}
      </div>
    </>
  );
};


