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

interface DockerStatus {
  running: boolean | null;
  container: string;
  status: string;
  message?: string;
}

export const DatabaseAdmin = () => {
  const [status, setStatus] = useState<DatabaseStatus | null>(null);
  const [dockerStatus, setDockerStatus] = useState<DockerStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [startingDocker, setStartingDocker] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetchDockerStatus = async () => {
    try {
      const data = await api.database.dockerStatus();
      setDockerStatus(data);
    } catch {
      // Docker status endpoint might fail if API can't reach docker
      setDockerStatus({ running: null, container: 'pitwall_postgres', status: 'unknown' });
    }
  };

  const fetchStatus = async () => {
    try {
      const data = await api.database.status();
      setStatus(data);
      setError(null);
      // Also fetch docker status
      fetchDockerStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
      // Still try to get docker status even if main status fails
      fetchDockerStatus();
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

  const handleStartDocker = async () => {
    setStartingDocker(true);
    setMessage(null);
    setError(null);
    try {
      const result = await api.database.startDocker();
      setMessage(result.message);
      // Refresh status after starting
      setTimeout(() => {
        fetchStatus();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start Docker container');
    } finally {
      setStartingDocker(false);
    }
  };

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

      {/* Docker Status */}
      {dockerStatus && (
        <div className={`p-4 rounded-lg border ${
          dockerStatus.running === true 
            ? 'bg-green-500/10 border-green-500/30' 
            : dockerStatus.running === false 
              ? 'bg-orange-500/10 border-orange-500/30'
              : 'bg-zinc-800/50 border-zinc-700'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Docker whale icon */}
              <svg className={`w-6 h-6 ${
                dockerStatus.running === true 
                  ? 'text-green-400' 
                  : dockerStatus.running === false 
                    ? 'text-orange-400'
                    : 'text-zinc-500'
              }`} viewBox="0 0 24 24" fill="currentColor">
                <path d="M13.983 11.078h2.119a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.119a.185.185 0 00-.185.185v1.888c0 .102.083.185.185.185m-2.954-5.43h2.118a.186.186 0 00.186-.186V3.574a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.186m0 2.716h2.118a.187.187 0 00.186-.186V6.29a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.887c0 .102.082.185.185.186m-2.93 0h2.12a.186.186 0 00.184-.186V6.29a.185.185 0 00-.185-.185H8.1a.185.185 0 00-.185.185v1.887c0 .102.083.185.185.186m-2.964 0h2.119a.186.186 0 00.185-.186V6.29a.185.185 0 00-.185-.185H5.136a.186.186 0 00-.186.185v1.887c0 .102.084.185.186.186m5.893 2.715h2.118a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.185m-2.93 0h2.12a.185.185 0 00.184-.185V9.006a.185.185 0 00-.184-.186h-2.12a.185.185 0 00-.184.185v1.888c0 .102.083.185.185.185m-2.964 0h2.119a.185.185 0 00.185-.185V9.006a.185.185 0 00-.185-.186h-2.12a.186.186 0 00-.185.186v1.887c0 .102.084.185.186.185m-2.92 0h2.12a.185.185 0 00.184-.185V9.006a.185.185 0 00-.184-.186h-2.12a.185.185 0 00-.184.185v1.888c0 .102.082.185.185.185M23.763 9.89c-.065-.051-.672-.51-1.954-.51-.338.001-.676.03-1.01.087-.248-1.7-1.653-2.53-1.716-2.566l-.344-.199-.226.327c-.284.438-.49.922-.612 1.43-.23.97-.09 1.882.403 2.661-.595.332-1.55.413-1.744.42H.751a.751.751 0 00-.75.748 11.376 11.376 0 00.692 4.062c.545 1.428 1.355 2.48 2.41 3.124 1.18.723 3.1 1.137 5.275 1.137.983.003 1.963-.086 2.93-.266a12.248 12.248 0 003.823-1.389c.98-.567 1.86-1.288 2.61-2.136 1.252-1.418 1.998-2.997 2.553-4.4h.221c1.372 0 2.215-.549 2.68-1.009.309-.293.55-.65.707-1.046l.098-.288Z"/>
              </svg>
              <div>
                <div className={`font-medium ${
                  dockerStatus.running === true 
                    ? 'text-green-400' 
                    : dockerStatus.running === false 
                      ? 'text-orange-400'
                      : 'text-zinc-400'
                }`}>
                  {dockerStatus.running === true 
                    ? 'Docker DB Running' 
                    : dockerStatus.running === false 
                      ? 'Docker DB Stopped'
                      : 'Docker Status Unknown'}
                </div>
                <div className="text-xs text-zinc-500">
                  {dockerStatus.status}
                </div>
              </div>
            </div>
            
            {dockerStatus.running === false && (
              <button
                onClick={handleStartDocker}
                disabled={startingDocker}
                className={`py-2 px-4 rounded-lg font-medium text-sm transition-all flex items-center gap-2 ${
                  startingDocker
                    ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                    : 'bg-orange-600 hover:bg-orange-500 text-white'
                }`}
              >
                {startingDocker ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Starting...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Start Docker DB
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      )}

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
            <br />
            <span className="text-zinc-500">Docker controls are for local development only.</span>
          </div>
        </>
      )}
    </div>
  );
};

