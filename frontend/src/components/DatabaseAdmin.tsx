import { useState, useEffect } from 'react';
import { api } from '../api/client';

interface DatabaseStatus {
  database: {
    meetings: number;
    sessions: number;
    laps: number;
    drivers: number;
    latest_season: number;
    latest_meeting_date: string | null;
    latest_session?: {
      name: string;
      start_time: string;
      meeting_id: string;
    };
  };
  update: {
    is_running: boolean;
    started_at: string | null;
    completed_at: string | null;
    phase: string | null;
    success: boolean | null;
    error: string | null;
    log_file: string | null;
  };
}

export const DatabaseAdmin = () => {
  const [status, setStatus] = useState<DatabaseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await api.database.status();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll for status while update is running
    const interval = setInterval(() => {
      if (status?.update.is_running) {
        fetchStatus();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [status?.update.is_running]);

  const handleUpdate = async () => {
    setUpdating(true);
    setMessage(null);
    setError(null);
    try {
      await api.database.update(true); // Skip high volume for faster updates
      setMessage('Database update started! This may take a few minutes...');
      fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start update');
    } finally {
      setUpdating(false);
    }
  };

  const handleRefreshGold = async () => {
    setRefreshing(true);
    setMessage(null);
    setError(null);
    try {
      const result = await api.database.refreshGold();
      setMessage(`${result.message} - ${result.results.success.length} views refreshed`);
      fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh views');
    } finally {
      setRefreshing(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const formatNumber = (num: number) => {
    return num.toLocaleString();
  };

  if (loading) {
    return (
      <div className="p-6 bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="animate-pulse flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-red-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-zinc-400">Loading database status...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-zinc-900 rounded-lg border border-zinc-800 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
          </svg>
          Database Admin
        </h2>
        <button
          onClick={fetchStatus}
          className="p-2 text-zinc-400 hover:text-white transition-colors"
          title="Refresh Status"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}
      {message && (
        <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-sm">
          {message}
        </div>
      )}

      {/* Database Stats */}
      {status && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-zinc-800/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-white">{formatNumber(status.database.meetings)}</div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Meetings</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-white">{formatNumber(status.database.sessions)}</div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Sessions</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-white">{formatNumber(status.database.laps)}</div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Laps</div>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-4">
              <div className="text-2xl font-bold text-white">{formatNumber(status.database.drivers)}</div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Drivers</div>
            </div>
          </div>

          {/* Latest Data Info */}
          <div className="bg-zinc-800/30 rounded-lg p-4 space-y-2">
            <div className="text-sm text-zinc-400">
              <span className="text-zinc-500">Latest Season:</span>{' '}
              <span className="text-white font-medium">{status.database.latest_season}</span>
            </div>
            {status.database.latest_session && (
              <div className="text-sm text-zinc-400">
                <span className="text-zinc-500">Latest Session:</span>{' '}
                <span className="text-white font-medium">{status.database.latest_session.name}</span>
                <span className="text-zinc-600"> • </span>
                <span className="text-zinc-500">{formatDate(status.database.latest_session.start_time)}</span>
              </div>
            )}
          </div>

          {/* Update Status */}
          {status.update.is_running && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
                <div>
                  <div className="text-yellow-400 font-medium">Update in Progress</div>
                  <div className="text-sm text-yellow-400/70">
                    Phase: {status.update.phase} • Started: {formatDate(status.update.started_at)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {status.update.completed_at && !status.update.is_running && (
            <div className={`rounded-lg p-4 ${
              status.update.success 
                ? 'bg-green-500/10 border border-green-500/30' 
                : 'bg-red-500/10 border border-red-500/30'
            }`}>
              <div className="text-sm">
                <span className={status.update.success ? 'text-green-400' : 'text-red-400'}>
                  Last update: {status.update.success ? 'Successful' : 'Failed'}
                </span>
                <span className="text-zinc-500"> • </span>
                <span className="text-zinc-400">{formatDate(status.update.completed_at)}</span>
              </div>
              {status.update.error && (
                <div className="text-xs text-red-400/70 mt-1 font-mono">{status.update.error}</div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleUpdate}
              disabled={updating || status.update.is_running}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
                updating || status.update.is_running
                  ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-500 text-white'
              }`}
            >
              {(updating || status.update.is_running) ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  Updating...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Update Database
                </>
              )}
            </button>
            
            <button
              onClick={handleRefreshGold}
              disabled={refreshing || status.update.is_running}
              className={`py-3 px-4 rounded-lg font-medium transition-all flex items-center gap-2 ${
                refreshing || status.update.is_running
                  ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                  : 'bg-zinc-700 hover:bg-zinc-600 text-white'
              }`}
            >
              {refreshing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  Refreshing...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Refresh Views
                </>
              )}
            </button>
          </div>

          <div className="text-xs text-zinc-600 text-center">
            Full update fetches new data from OpenF1 API → transforms to silver → refreshes gold views.
            <br />
            "Refresh Views" only refreshes the gold materialized views (faster).
          </div>
        </>
      )}
    </div>
  );
};

