import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { Button } from '../components/Button';
import { faArrowLeft } from '@fortawesome/free-solid-svg-icons';
import { api } from '../api/client';

interface SessionData {
  session_id: string;
  season: number;
  round_number: number;
  meeting_official_name: string;
  circuit_id: string;
  circuit_name: string;
  circuit_short_name: string;
  session_type: string;
  start_time: string;
  end_time: string | null;
  scheduled_laps: number | null;
  completed_laps: number | null;
  winner_driver_id: string | null;
  winner_team_id: string | null;
  winner_driver_name: string | null;
  winner_team_name: string | null;
  weather_conditions: string | null;
  air_temperature: number | null;
  track_temperature: number | null;
  red_flag_count: number;
  yellow_flag_count: number;
  safety_car_count: number;
  virtual_safety_car_count: number;
}

interface ClassificationData {
  driver_id: string;
  driver_number: number;
  driver_name: string;
  name_acronym: string;
  team_id: string;
  team_name: string;
  display_name: string | null;
  color_hex: string;
  logo_url: string | null;
  grid_position: number | null;
  finish_position: number | null;
  status: string;
  laps_completed: number | null;
  duration_ms: number | null;
  gap_to_leader_ms: number | null;
  best_lap_ms: number | null;
  fastest_lap: boolean | null;
  points: number | null;
}

export const SessionDetails = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<SessionData | null>(null);
  const [classification, setClassification] = useState<ClassificationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!sessionId) return;
      
      setLoading(true);
      setError(null);
      
      try {
        // Fetch session summary
        const sessionData = await api.session(sessionId);
        setSession(sessionData);

        // Fetch classification
        const classificationData = await api.sessionClassification(sessionId);
        setClassification(classificationData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load session details');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [sessionId]);

  const formatTime = (timeStr: string) => {
    const date = new Date(timeStr);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (ms: number | null) => {
    if (ms === null || ms === undefined) return '-';
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const milliseconds = ms % 1000;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
  };

  const formatGap = (gapMs: number | null) => {
    if (gapMs === null || gapMs === undefined || gapMs === 0) return '-';
    const seconds = (gapMs / 1000).toFixed(3);
    return `+${seconds}s`;
  };

  const isRaceSession = (sessionType: string) => {
    return sessionType === 'race' || sessionType === 'sprint';
  };

  const getSessionDisplayName = (sessionType: string) => {
    switch (sessionType) {
      case 'p1':
        return 'Practice 1';
      case 'p2':
        return 'Practice 2';
      case 'p3':
        return 'Practice 3';
      case 'sprint_quali':
        return 'Sprint Qualifying';
      case 'sprint':
        return 'Sprint';
      case 'quali':
        return 'Qualifying';
      case 'race':
        return 'Race';
      default:
        return sessionType;
    }
  };

  if (loading) {
    return (
      <PageLayout pageTitle="Session Details" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-f1-red"></div>
        </div>
      </PageLayout>
    );
  }

  if (error || !session) {
    return (
      <PageLayout pageTitle="Session Details" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <p className="text-f1-red text-lg">{error || 'Session not found'}</p>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout 
      pageTitle={`${session.circuit_short_name} ${session.session_type}`}
      sidebar={<NavSidebar />}
    >
      <div className="flex flex-col h-full gap-6">
        {/* Back button */}
        <div>
          <Button 
            variant="text" 
            size="sm"
            icon={faArrowLeft}
            onClick={() => navigate(-1)}
          >
            Back
          </Button>
        </div>

        {/* Session Header */}
        <div className="bg-black rounded-corner p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-white f1-display-bold text-3xl mb-2">
                {session.meeting_official_name}
              </h1>
              <h2 className="text-zinc-400 f1-display-regular text-xl">
                {getSessionDisplayName(session.session_type)}
              </h2>
            </div>
            {session.winner_driver_name && (
              <div className="text-right">
                <div className="text-zinc-400 text-sm f1-display-regular mb-1">Winner</div>
                <div className="text-white f1-display-bold text-2xl">
                  {session.winner_driver_name}
                </div>
                <div className="text-zinc-400 f1-display-regular text-sm">
                  {session.winner_team_name}
                </div>
              </div>
            )}
          </div>

          {/* Session Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 pt-4 border-t border-zinc-800">
            <div>
              <div className="text-zinc-400 text-sm f1-display-regular mb-1">Circuit</div>
              <div className="text-white f1-display-bold">{session.circuit_name}</div>
            </div>
            <div>
              <div className="text-zinc-400 text-sm f1-display-regular mb-1">Start Time</div>
              <div className="text-white f1-display-bold">{formatTime(session.start_time)}</div>
            </div>
            {session.completed_laps !== null && (
              <div>
                <div className="text-zinc-400 text-sm f1-display-regular mb-1">Laps</div>
                <div className="text-white f1-display-bold">
                  {session.completed_laps}{session.scheduled_laps ? `/${session.scheduled_laps}` : ''}
                </div>
              </div>
            )}
            {session.weather_conditions && (
              <div>
                <div className="text-zinc-400 text-sm f1-display-regular mb-1">Weather</div>
                <div className="text-white f1-display-bold capitalize">{session.weather_conditions}</div>
              </div>
            )}
            {session.air_temperature !== null && (
              <div>
                <div className="text-zinc-400 text-sm f1-display-regular mb-1">Air Temp</div>
                <div className="text-white f1-display-bold">{session.air_temperature.toFixed(1)}°C</div>
              </div>
            )}
            {session.track_temperature !== null && (
              <div>
                <div className="text-zinc-400 text-sm f1-display-regular mb-1">Track Temp</div>
                <div className="text-white f1-display-bold">{session.track_temperature.toFixed(1)}°C</div>
              </div>
            )}
          </div>

          {/* Flags */}
          {(session.red_flag_count > 0 || session.yellow_flag_count > 0 || session.safety_car_count > 0 || session.virtual_safety_car_count > 0) && (
            <div className="flex gap-4 pt-4 mt-4 border-t border-zinc-800">
              {session.red_flag_count > 0 && (
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-red-600 rounded"></div>
                  <span className="text-white f1-display-regular">{session.red_flag_count} Red Flag{session.red_flag_count > 1 ? 's' : ''}</span>
                </div>
              )}
              {session.yellow_flag_count > 0 && (
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-yellow-400 rounded"></div>
                  <span className="text-white f1-display-regular">{session.yellow_flag_count} Yellow Flag{session.yellow_flag_count > 1 ? 's' : ''}</span>
                </div>
              )}
              {session.safety_car_count > 0 && (
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-orange-400 rounded"></div>
                  <span className="text-white f1-display-regular">{session.safety_car_count} Safety Car{session.safety_car_count > 1 ? 's' : ''}</span>
                </div>
              )}
              {session.virtual_safety_car_count > 0 && (
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 bg-orange-600 rounded"></div>
                  <span className="text-white f1-display-regular">{session.virtual_safety_car_count} VSC{session.virtual_safety_car_count > 1 ? 's' : ''}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Classification Table */}
        <div className="flex-1 bg-black rounded-corner overflow-hidden flex flex-col">
          <div className="p-6 border-b border-zinc-800">
            <h2 className="text-white f1-display-bold text-2xl">
              {isRaceSession(session.session_type) ? 'Results' : 'Classification'}
            </h2>
          </div>
          
          <div className="flex-1 overflow-auto">
            <table className="w-full">
              <thead className="sticky top-0 bg-black">
                <tr>
                  <th className="text-left text-zinc-400 f1-display-regular text-sm p-4 w-16">POS</th>
                  <th className="text-left text-zinc-400 f1-display-regular text-sm p-4">DRIVER</th>
                  <th className="text-left text-zinc-400 f1-display-regular text-sm p-4">TEAM</th>
                  {isRaceSession(session.session_type) && (
                    <>
                      <th className="text-left text-zinc-400 f1-display-regular text-sm p-4">TIME</th>
                      <th className="text-left text-zinc-400 f1-display-regular text-sm p-4">GAP</th>
                      <th className="text-right text-zinc-400 f1-display-regular text-sm p-4">PTS</th>
                    </>
                  )}
                  {!isRaceSession(session.session_type) && (
                    <>
                      <th className="text-left text-zinc-400 f1-display-regular text-sm p-4">TIME</th>
                      <th className="text-left text-zinc-400 f1-display-regular text-sm p-4">GAP</th>
                      <th className="text-left text-zinc-400 f1-display-regular text-sm p-4">LAPS</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {classification.map((entry, index) => (
                  <tr 
                    key={entry.driver_id}
                    className="border-t border-zinc-800 hover:bg-zinc-900 transition-colors"
                  >
                    <td className="text-white f1-display-bold text-lg p-4">
                      {entry.finish_position || index + 1}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <span className="text-white f1-display-regular text-lg">
                          {entry.driver_name}
                        </span>
                        <span className="text-zinc-500 f1-display-regular text-sm">
                          {entry.name_acronym}
                        </span>
                        <span className="text-zinc-500 f1-display-regular text-sm">
                          #{entry.driver_number}
                        </span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        {entry.logo_url && (
                          <img 
                            src={entry.logo_url} 
                            alt={entry.team_name}
                            className="w-5 h-5 object-contain"
                          />
                        )}
                        <span className="text-zinc-400 f1-display-regular">
                          {entry.team_name}
                        </span>
                      </div>
                    </td>
                    {isRaceSession(session.session_type) && (
                      <>
                        <td className="text-white f1-display-regular p-4">
                          {entry.status !== 'finished' 
                            ? entry.status.toUpperCase()
                            : formatDuration(entry.duration_ms)}
                        </td>
                        <td className="text-zinc-400 f1-display-regular p-4">
                          {formatGap(entry.gap_to_leader_ms)}
                        </td>
                        <td className="text-white f1-display-bold text-right p-4">
                          {entry.points || '-'}
                        </td>
                      </>
                    )}
                    {!isRaceSession(session.session_type) && (
                      <>
                        <td className="text-white f1-display-regular p-4">
                          {formatDuration(entry.best_lap_ms)}
                        </td>
                        <td className="text-zinc-400 f1-display-regular p-4">
                          {formatGap(entry.gap_to_leader_ms)}
                        </td>
                        <td className="text-white f1-display-regular p-4">
                          {entry.laps_completed || '-'}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

