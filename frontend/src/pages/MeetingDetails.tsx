import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { Button } from '../components/Button';
import { TabButton } from '../components/TabButton';
import { SessionResultsTable } from '../components/DataTable/SessionResultsTable';
import { FontAwesomeIcon } from '../lib/fontawesome';
import { 
  faArrowLeft, 
  faCloudRain, 
  faSun, 
  faMoon,
} from '@fortawesome/free-solid-svg-icons';
import { api } from '../api/client';

interface MeetingData {
  meeting_id: string;
  season: number;
  round_number: number;
  meeting_official_name: string;
  meeting_short_name: string;
  circuit_name: string;
  circuit_short_name: string;
  circuit_id: string;
  location: string;
  country_code: string;
  country_name: string;
  flag_url: string | null;
  circuit_svg: string | null;
  date_start: string;
  date_end: string;
}

interface SessionData {
  session_id: string;
  session_type: string;
  start_time: string;
  end_time: string | null;
  scheduled_laps: number | null;
  completed_laps: number | null;
  winner_driver_id: string | null;
  winner_team_id: string | null;
  red_flag_count: number;
  safety_car_laps: number;
  vsc_laps: number;
  avg_air_temp_c: number | null;
  avg_track_temp_c: number | null;
  rain_flag: boolean;
}

interface ClassificationData {
  session_id: string;
  driver_id: string;
  driver_number: number;
  driver_name: string;
  name_acronym: string;
  team_id: string;
  team_name: string;
  display_name: string;
  color_hex: string;
  logo_url: string | null;
  headshot_url: string | null;
  headshot_override: string | null;
  grid_position: number | null;
  finish_position: number;
  status: string;
  laps_completed: number;
  duration_ms: number | null;
  gap_to_leader_ms: number | null;
  best_lap_ms: number | null;
  quali_lap_ms: number | null;
  fastest_lap: boolean;
  points: number | null;
}

export const MeetingDetails = () => {
  const { meetingId } = useParams<{ meetingId: string }>();
  const [meeting, setMeeting] = useState<MeetingData | null>(null);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [classification, setClassification] = useState<ClassificationData[]>([]);
  const [coverImageUrl, setCoverImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      if (!meetingId) return;
      
      setLoading(true);
      setError(null);
      
      try {
        // Fetch meeting details
        const meetingData = await api.meeting(meetingId);
        setMeeting(meetingData);

        // Fetch sessions for this meeting
        const sessionsData = await api.meetingSessions(meetingId);
        
        // Sort sessions by start_time descending (most recent first)
        const sortedSessions = [...sessionsData].sort((a, b) => 
          new Date(b.start_time).getTime() - new Date(a.start_time).getTime()
        );
        setSessions(sortedSessions);

        // Select the most recent session by default
        if (sortedSessions.length > 0) {
          setSelectedSessionId(sortedSessions[0].session_id);
        }

        // Fetch cover image for the circuit
        try {
          const images = await api.images({
            circuitId: meetingData.circuit_id,
            coverOnly: true,
          });
          if (images && images.length > 0) {
            setCoverImageUrl(`/assets/circuit_image/${images[0].file_path}`);
          }
        } catch {
          // Ignore image errors
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load meeting details');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [meetingId]);

  // Fetch classification when selected session changes
  useEffect(() => {
    const fetchClassification = async () => {
      if (!selectedSessionId) return;
      
      try {
        const data = await api.sessionClassification(selectedSessionId);
        setClassification(data);
      } catch (err) {
        console.error('Failed to load classification:', err);
        setClassification([]);
      }
    };

    fetchClassification();
  }, [selectedSessionId]);

  const getCircuitDisplayName = (): string => {
    if (!meeting) return '';
    if (meeting.circuit_name) {
      return meeting.circuit_name;
    }
    if (meeting.circuit_short_name.toLowerCase().includes('circuit')) {
      return meeting.circuit_short_name;
    }
    return `${meeting.circuit_short_name} Circuit`;
  };

  const getLocationDisplay = (): string => {
    if (!meeting) return '';
    // Omit location if it's the same as country (e.g., "Monaco, Monaco" → "Monaco")
    if (meeting.location === meeting.country_name) {
      return meeting.country_name;
    }
    return `${meeting.location}, ${meeting.country_name}`;
  };

  const getMeetingDateRange = (): string => {
    if (!sessions.length) return '';
    
    // Find the earliest session date
    const firstSessionDate = sessions.reduce((earliest, session) => {
      const sessionDate = new Date(session.start_time);
      return sessionDate < earliest ? sessionDate : earliest;
    }, new Date(sessions[0].start_time));

    // Calculate end date (first session + 2 days = 3 days total)
    const endDate = new Date(firstSessionDate);
    endDate.setDate(endDate.getDate() + 2);

    const formatDate = (date: Date) => {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    return `${formatDate(firstSessionDate)} - ${formatDate(endDate)}`;
  };

  const getSessionDisplayName = (sessionType: string) => {
    switch (sessionType) {
      case 'p1': return 'Practice 1';
      case 'p2': return 'Practice 2';
      case 'p3': return 'Practice 3';
      case 'sprint_quali': return 'Sprint Qualifying';
      case 'sprint': return 'Sprint';
      case 'quali': return 'Qualifying';
      case 'race': return 'Race';
      default: return sessionType;
    }
  };

  const formatTime = (ms: number | null): string => {
    if (ms === null || ms === undefined) return '-';
    const totalSeconds = ms / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    if (minutes > 0) {
      return `${minutes}:${seconds.toFixed(3).padStart(6, '0')}`;
    }
    return `${seconds.toFixed(3)}`;
  };

  const formatLapTime = (ms: number | null): string => {
    if (ms === null || ms === undefined) return '-';
    const totalSeconds = ms / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toFixed(3).padStart(6, '0')}`;
  };

  const formatGap = (ms: number | null): string => {
    if (ms === null || ms === undefined || ms === 0) return '-';
    const totalSeconds = ms / 1000;
    return `+${totalSeconds.toFixed(3)}s`;
  };

  const getWeatherIcon = (session: SessionData) => {
    if (session.rain_flag) {
      return faCloudRain;
    }
    // Determine day/night by time (simplified)
    const hour = new Date(session.start_time).getHours();
    const isNight = hour >= 18 || hour < 6;
    return isNight ? faMoon : faSun;
  };

  const getLatestSession = (): SessionData | null => {
    return sessions.length > 0 ? sessions[0] : null;
  };

  if (loading) {
    return (
      <PageLayout pageTitle="Grand Prix" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-f1-red"></div>
        </div>
      </PageLayout>
    );
  }

  if (error || !meeting) {
    return (
      <PageLayout pageTitle="Grand Prix" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <p className="text-f1-red text-lg">{error || 'Meeting not found'}</p>
        </div>
      </PageLayout>
    );
  }

  const latestSession = getLatestSession();
  const latestSessionClassification = latestSession 
    ? classification.filter(c => c.session_id === latestSession.session_id).slice(0, 3)
    : [];
  const latestSessionIsRaceOrSprint = latestSession && ['race', 'sprint'].includes(latestSession.session_type);
  const selectedSession = sessions.find(s => s.session_id === selectedSessionId);
  const isRaceOrSprint = selectedSession && ['race', 'sprint'].includes(selectedSession.session_type);

  return (
    <PageLayout 
      pageTitle={`${meeting.season} ${meeting.meeting_short_name}`}
      sidebar={<NavSidebar />}
    >
      <div className="flex h-full gap-4">
        {/* Left Sidebar - Fixed 360px */}
        <div className="w-[360px] flex-shrink-0 flex flex-col gap-4 overflow-y-auto">
          {/* Back button */}
          <Button 
            variant="text" 
            size="sm"
            icon={faArrowLeft}
            onClick={() => navigate('/grand-prix')}
          >
            Back to Grand Prix
          </Button>

          {/* Circuit Photo & Meeting Header */}
          <div className="bg-black rounded-corner overflow-hidden">
            {/* Circuit Photo */}
            <div className="relative h-[240px]">
              {coverImageUrl ? (
                <img
                  src={coverImageUrl}
                  alt={meeting.circuit_name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full bg-zinc-900" />
              )}
              
              {/* Gradient overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/20" />
              
              {/* Meeting Name */}
              <div className="absolute bottom-4 left-4 right-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="bg-f1-red text-white px-2 py-0.5 rounded text-xs f1-display-bold">
                    ROUND {meeting.round_number}
                  </div>
                  {meeting.flag_url && (
                    <div className="w-6 h-6 rounded-full overflow-hidden shadow-lg flex-shrink-0">
                      <img
                        src={meeting.flag_url}
                        alt={meeting.country_name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}
                </div>
                <h1 
                  className="text-white f1-display-bold text-2xl leading-tight uppercase"
                  style={{ textShadow: '0 2px 8px rgba(0,0,0,0.9)' }}
                >
                  {meeting.meeting_short_name}
                </h1>
              </div>
            </div>

            {/* Meeting Details */}
            <div className="p-4 space-y-3">
              {/* Date */}
              <div>
                <div className="text-zinc-500 text-xs uppercase tracking-wide mb-1">Date</div>
                <div className="text-white text-sm">{getMeetingDateRange()}</div>
              </div>

              {/* Circuit */}
              <div>
                <div className="text-zinc-500 text-xs uppercase tracking-wide mb-1">Circuit</div>
                <button
                  onClick={() => navigate(`/circuits/${meeting.circuit_id}`)}
                  className="text-white text-sm hover:text-f1-red transition-colors text-left font-semibold"
                >
                  {getCircuitDisplayName()}
                </button>
              </div>

              {/* Location */}
              <div>
                <div className="text-zinc-500 text-xs uppercase tracking-wide mb-1">Location</div>
                <div className="text-white text-sm">{getLocationDisplay()}</div>
              </div>
            </div>
          </div>

          {/* Track SVG */}
          {meeting.circuit_svg && (
            <button
              onClick={() => navigate(`/circuits/${meeting.circuit_id}`)}
              className="bg-black rounded-corner p-6 hover:bg-zinc-900 transition-colors"
            >
              <img 
                src={meeting.circuit_svg}
                alt={`${meeting.circuit_short_name} track layout`}
                className="w-full h-auto max-h-[200px] object-contain"
              />
            </button>
          )}

          {/* Latest Session Summary */}
          {latestSession && (
            <div className="bg-black rounded-corner p-4">
              <h3 className="text-white f1-display-bold text-sm uppercase mb-3">
                Latest Session
              </h3>
              
              {/* Session Name */}
              <div className="text-f1-red f1-display-bold text-lg mb-3">
                {getSessionDisplayName(latestSession.session_type)}
              </div>

              {/* Weather & Flags */}
              <div className="grid grid-cols-2 gap-2 mb-4 text-xs">
                {/* Weather */}
                <div className="bg-zinc-900 rounded p-2">
                  <div className="text-zinc-500 mb-1">Weather</div>
                  <div className="flex items-center gap-2">
                    <FontAwesomeIcon icon={getWeatherIcon(latestSession)} className="text-white" />
                    <span className="text-white font-mono">
                      {latestSession.avg_air_temp_c?.toFixed(0) || '-'}°C
                    </span>
                  </div>
                </div>

                {/* Flags */}
                <div className="bg-zinc-900 rounded p-2">
                  <div className="text-zinc-500 mb-1">Flags</div>
                  <div className="flex items-center gap-2 text-white font-mono">
                    {latestSession.red_flag_count > 0 && (
                      <span className="text-red-500">🚩{latestSession.red_flag_count}</span>
                    )}
                    {latestSession.safety_car_laps > 0 && (
                      <span>SC:{latestSession.safety_car_laps}</span>
                    )}
                    {latestSession.vsc_laps > 0 && (
                      <span>VSC:{latestSession.vsc_laps}</span>
                    )}
                    {latestSession.red_flag_count === 0 && 
                     latestSession.safety_car_laps === 0 && 
                     latestSession.vsc_laps === 0 && <span>-</span>}
                  </div>
                </div>
              </div>

              {/* Top 3 Results */}
              {latestSessionClassification.length > 0 && (
                <div className="space-y-2">
                  <div className="text-zinc-500 text-xs uppercase tracking-wide">Top 3</div>
                  {latestSessionClassification.map((result, index) => (
                    <div 
                      key={result.driver_id}
                      className="flex items-center gap-2 bg-zinc-900 rounded p-2"
                    >
                      {/* Position */}
                      <div className="w-6 text-center font-mono text-sm text-zinc-500">
                        {index + 1}
                      </div>
                      
                      {/* Driver Avatar/Logo */}
                      <div className="w-6 h-6 rounded overflow-hidden bg-zinc-800 flex-shrink-0">
                        {result.logo_url && (
                          <img 
                            src={result.logo_url} 
                            alt={result.team_name}
                            className="w-full h-full object-contain"
                          />
                        )}
                      </div>

                      {/* Driver Name */}
                      <div className="flex-1 min-w-0">
                        <div className="text-white text-sm font-semibold truncate">
                          {result.driver_name.split(' ').pop()}
                        </div>
                      </div>

                      {/* Time/Gap */}
                      <div className="text-zinc-400 text-xs font-mono">
                        {index === 0 
                          ? (latestSessionIsRaceOrSprint 
                              ? formatTime(result.duration_ms) 
                              : formatLapTime(result.quali_lap_ms || result.best_lap_ms))
                          : (latestSessionIsRaceOrSprint 
                              ? formatGap(result.gap_to_leader_ms) 
                              : formatGap((result.quali_lap_ms || result.best_lap_ms) 
                                  ? ((result.quali_lap_ms || result.best_lap_ms)! - (latestSessionClassification[0].quali_lap_ms || latestSessionClassification[0].best_lap_ms || 0)) 
                                  : null))
                        }
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Main Content - Right Side */}
        <div className="flex-1 min-w-0 flex flex-col gap-4 overflow-hidden">
          {/* Session Tabs */}
          <div className="flex gap-2 flex-wrap">
            {sessions.map((session) => (
              <TabButton
                key={session.session_id}
                variant="ghost"
                size="md"
                active={session.session_id === selectedSessionId}
                onClick={() => setSelectedSessionId(session.session_id)}
              >
                {getSessionDisplayName(session.session_type)}
              </TabButton>
            ))}
          </div>

          {/* Selected Session Results Table */}
          <div className="flex-1 overflow-y-auto bg-black rounded-corner p-4">
            {selectedSession && classification.length > 0 ? (
              <SessionResultsTable
                results={classification.map(c => ({
                  driver_id: c.driver_id,
                  driver_number: c.driver_number,
                  driver_name: c.driver_name,
                  name_acronym: c.name_acronym,
                  team_name: c.team_name,
                  team_logo_url: c.logo_url || undefined,
                  team_color: c.color_hex,
                  headshot_url: c.headshot_url || undefined,
                  headshot_override: c.headshot_override || undefined,
                  grid_position: c.grid_position,
                  finish_position: c.finish_position,
                  duration_ms: c.duration_ms,
                  gap_to_leader_ms: c.gap_to_leader_ms,
                  best_lap_ms: c.best_lap_ms,
                  quali_lap_ms: c.quali_lap_ms,
                  points: c.points,
                  fastest_lap: c.fastest_lap,
                  status: c.status,
                }))}
                sessionType={isRaceOrSprint ? (selectedSession.session_type as 'race' | 'sprint') : 'qualifying'}
                showPositionChange={isRaceOrSprint}
                showPoints={isRaceOrSprint}
                showFastestLap={isRaceOrSprint}
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-zinc-500">No results available for this session</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
};
