import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

interface UpdateStatus {
  is_running: boolean;
  phase: string | null;
  started_at: string | null;
}

export const DatabaseUpdateIndicator = () => {
  const [status, setStatus] = useState<UpdateStatus | null>(null);

  useEffect(() => {
    let mounted = true;
    let pollInterval: ReturnType<typeof setInterval> | null = null;

    const fetchStatus = async () => {
      try {
        const data = await api.database.status();
        if (mounted) {
          setStatus(data.update);
        }
      } catch {
        // Silently fail - don't show indicator if API is down
        if (mounted) {
          setStatus(null);
        }
      }
    };

    // Initial fetch
    fetchStatus();

    // Poll every 3 seconds
    pollInterval = setInterval(fetchStatus, 3000);

    return () => {
      mounted = false;
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, []);

  // Don't show anything if no update is running
  if (!status?.is_running) {
    return null;
  }

  const getPhaseText = (phase: string | null) => {
    switch (phase) {
      case 'queued':
        return 'Starting...';
      case 'starting':
        return 'Starting...';
      case 'running':
        return 'Updating...';
      case 'completed':
        return 'Complete';
      case 'failed':
        return 'Failed';
      default:
        return 'Updating...';
    }
  };

  return (
    <Link
      to="/admin"
      className="flex items-center gap-2 px-3 py-1.5 bg-yellow-500/10 border border-yellow-500/30 rounded-full text-yellow-400 text-xs font-medium hover:bg-yellow-500/20 transition-colors"
    >
      {/* Animated spinner */}
      <svg
        className="w-3.5 h-3.5 animate-spin"
        viewBox="0 0 24 24"
        fill="none"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="3"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <span>{getPhaseText(status.phase)}</span>
    </Link>
  );
};

