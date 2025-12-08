import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { Button } from '../components/Button';
import { TabButton } from '../components/TabButton';
import { SessionResultsTable } from '../components/DataTable/SessionResultsTable';
import { LapChart, type LapChartData } from '../components/LapChart';
import { FontAwesomeIcon } from '../lib/fontawesome';
import { 
  faArrowLeft, 
  faCloudRain, 
  faSun, 
  faMoon,
} from '@fortawesome/free-solid-svg-icons';
import { api } from '../api/client';
import { Group } from '@visx/group';
import { LinePath } from '@visx/shape';
import { scaleLinear } from '@visx/scale';
import { AxisLeft, AxisBottom } from '@visx/axis';

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


interface LapTimeRow {
  season: number;
  round_number: number;
  meeting_official_name: string;
  session_type: string;
  session_id: string;
  driver_id: string;
  driver_number: number;
  driver_name: string;
  name_acronym: string;
  team_id: string;
  team_name: string;
  display_name: string;
  color_hex: string;
  lap_number: number;
  date_start: string;
  lap_duration_ms: number | null;
  duration_s1_ms: number | null;
  duration_s2_ms: number | null;
  duration_s3_ms: number | null;
  s1_segments: number[] | null;
  s2_segments: number[] | null;
  s3_segments: number[] | null;
  i1_speed_kph: number | null;
  i2_speed_kph: number | null;
  st_speed_kph: number | null;
  is_pit_in_lap: boolean;
  is_pit_out_lap: boolean;
  is_valid: boolean;
  lap_time_s: number | null;
  cumulative_time_ms: number | null;
}
type DetailTab = 'results' | 'lap-chart' | 'lap-times' | 'lap-pace';

export const MeetingDetails = () => {
  const { meetingId } = useParams<{ meetingId: string }>();
  const [meeting, setMeeting] = useState<MeetingData | null>(null);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [selectedDetailTab, setSelectedDetailTab] = useState<DetailTab>('results');
  const [classification, setClassification] = useState<ClassificationData[]>([]);
  const [lapChartData, setLapChartData] = useState<LapChartData[]>([]);
  const [lapTimes, setLapTimes] = useState<LapTimeRow[]>([]);
  const [lapTimesLoading, setLapTimesLoading] = useState(false);
  const [segmentMeaning, setSegmentMeaning] = useState<Record<number, { color_label: string | null; meaning: string | null }>>({});
  const [selectedLapTimesDriverId, setSelectedLapTimesDriverId] = useState<string | null>(null);
  const [selectedLapPaceDriverId, setSelectedLapPaceDriverId] = useState<string | null>(null);
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
        // Default lap times driver to first classification once loaded (set after classification fetch)

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

  // When classification changes for selected session, set default lap-times driver
  useEffect(() => {
    if (!selectedSessionId) return;
    if (selectedLapTimesDriverId) return;
    const firstDriver = classification.find(c => c.session_id === selectedSessionId);
    if (firstDriver) {
      setSelectedLapTimesDriverId(firstDriver.driver_id);
    }
  }, [classification, selectedSessionId, selectedLapTimesDriverId]);

  // Fetch segment meaning once
  useEffect(() => {
    const loadSegmentMeaning = async () => {
      try {
        const mapping = await api.segmentMeaning();
        const map: Record<number, { color_label: string | null; meaning: string | null }> = {};
        mapping.forEach((row: any) => {
          map[row.segment_value] = { color_label: row.color_label, meaning: row.meaning };
        });
        setSegmentMeaning(map);
      } catch (err) {
        console.error('Failed to load segment meaning:', err);
      }
    };
    loadSegmentMeaning();
  }, []);

  // Fetch lap chart data when selected session changes (only for race/sprint)
  useEffect(() => {
    const fetchLapChart = async () => {
      if (!selectedSessionId) return;
      
      // Check if this is a race or sprint session
      const session = sessions.find(s => s.session_id === selectedSessionId);
      if (!session || !['race', 'sprint'].includes(session.session_type)) {
        setLapChartData([]);
        return;
      }
      
      try {
        const data = await api.lapChart(selectedSessionId);
        setLapChartData(data);
      } catch (err) {
        console.error('Failed to load lap chart:', err);
        setLapChartData([]);
      }
    };

    fetchLapChart();
  }, [selectedSessionId, sessions]);

  // Fetch lap times (only race/sprint) when tab is lap-times
  useEffect(() => {
    const fetchLapTimes = async () => {
      if (!['lap-times', 'lap-pace'].includes(selectedDetailTab)) return;
      if (!selectedSessionId) return;
      const session = sessions.find(s => s.session_id === selectedSessionId);
      if (!session || !['race', 'sprint'].includes(session.session_type)) {
        setLapTimes([]);
        return;
      }
      try {
        setLapTimesLoading(true);
        const data = await api.lapTimes(selectedSessionId);
        setLapTimes(data || []);
        // Set default driver selections if not set
        const firstDriver = classification.find(c => c.session_id === selectedSessionId);
        if (firstDriver) {
          if (!selectedLapTimesDriverId) {
            setSelectedLapTimesDriverId(firstDriver.driver_id);
          }
          if (!selectedLapPaceDriverId) {
            setSelectedLapPaceDriverId(firstDriver.driver_id);
          }
        }
      } catch (err) {
        console.error('Failed to load lap times:', err);
        setLapTimes([]);
      } finally {
        setLapTimesLoading(false);
      }
    };
    fetchLapTimes();
  }, [selectedDetailTab, selectedSessionId, sessions, classification, selectedLapTimesDriverId, selectedLapPaceDriverId]);

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
        <div className="w-[360px] flex-shrink-0 relative flex flex-col gap-4 overflow-y-auto">
          {/* Back button - positioned absolutely on top */}
          <div className="absolute top-2 left-2 z-10">
            <Button 
              variant="secondary" 
              size="sm"
              icon={faArrowLeft}
              onClick={() => navigate('/grand-prix')}
              className="[&_*]:drop-shadow-[0_3px_3px_rgba(0,0,0,1)]"
            >
              Back to Grand Prix
            </Button>
          </div>

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
          {/* Session Details Tabs */}
          <div className="flex gap-2 flex-wrap">
            {sessions.map((session) => (
              <TabButton
                key={session.session_id}
                variant="default"
                size="md"
                active={session.session_id === selectedSessionId}
                onClick={() => setSelectedSessionId(session.session_id)}
              >
                {getSessionDisplayName(session.session_type)}
              </TabButton>
            ))}
          </div>

          {/* Selected Session Results Table */}
          <div className="flex-1 overflow-hidden bg-black rounded-corner flex flex-col">
            {/* Secondary Tabs */}
            <div className="flex gap-2 p-4 pb-0">
              <TabButton
                variant="ghost"
                size="sm"
                active={selectedDetailTab === 'results'}
                onClick={() => setSelectedDetailTab('results')}
              >
                Results
              </TabButton>
              {isRaceOrSprint && (
                <TabButton
                  variant="ghost"
                  size="sm"
                  active={selectedDetailTab === 'lap-chart'}
                  onClick={() => setSelectedDetailTab('lap-chart')}
                >
                  Lap Chart
                </TabButton>
              )}
              {isRaceOrSprint && (
                <TabButton
                  variant="ghost"
                  size="sm"
                  active={selectedDetailTab === 'lap-times'}
                  onClick={() => setSelectedDetailTab('lap-times')}
                >
                  Lap Times
                </TabButton>
              )}
              {isRaceOrSprint && (
                <TabButton
                  variant="ghost"
                  size="sm"
                  active={selectedDetailTab === 'lap-pace'}
                  onClick={() => setSelectedDetailTab('lap-pace')}
                >
                  Lap Pace
                </TabButton>
              )}
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-4 pt-4 pb-8">
              {selectedDetailTab === 'results' && (
                selectedSession && classification.length > 0 ? (
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
                )
              )}
              
              {selectedDetailTab === 'lap-chart' && (
                selectedSession && lapChartData.length > 0 ? (
                  <LapChart
                    data={lapChartData}
                    classification={classification.map(c => ({
                      driver_id: c.driver_id,
                      grid_position: c.grid_position,
                      finish_position: c.finish_position,
                      laps_completed: c.laps_completed,
                    }))}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full min-h-[400px]">
                    <p className="text-zinc-500">No lap chart data available for this session</p>
                  </div>
                )
              )}

              {selectedDetailTab === 'lap-times' && isRaceOrSprint && (
                <LapTimesTab
                  sessionId={selectedSessionId}
                  lapTimes={lapTimes}
                  lapTimesLoading={lapTimesLoading}
                  classification={classification}
                  selectedDriverId={selectedLapTimesDriverId}
                  onSelectDriver={setSelectedLapTimesDriverId}
                  segmentMeaning={segmentMeaning}
                />
              )}

              {selectedDetailTab === 'lap-pace' && isRaceOrSprint && (
                <LapPaceTab
                  sessionId={selectedSessionId}
                  lapTimes={lapTimes}
                  lapTimesLoading={lapTimesLoading}
                  classification={classification}
                  selectedDriverId={selectedLapPaceDriverId}
                  onSelectDriver={setSelectedLapPaceDriverId}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

interface LapTimesTabProps {
  sessionId: string | null;
  lapTimes: LapTimeRow[];
  lapTimesLoading: boolean;
  classification: ClassificationData[];
  selectedDriverId: string | null;
  onSelectDriver: (driverId: string | null) => void;
  segmentMeaning: Record<number, { color_label: string | null; meaning: string | null }>;
}

const LapTimesTab = ({
  sessionId,
  lapTimes,
  lapTimesLoading,
  classification,
  selectedDriverId,
  onSelectDriver,
  segmentMeaning,
}: LapTimesTabProps) => {
  if (!sessionId) return null;

  const formatLap = (ms: number | null | undefined) => {
    if (ms === null || ms === undefined) return '-';
    const totalSeconds = ms / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toFixed(3).padStart(6, '0')}`;
  };

  const driversForSession = classification.filter(c => c.session_id === sessionId);

  // Filter laps for selected driver
  const driverLapTimes = lapTimes.filter(l => l.session_id === sessionId && l.driver_id === selectedDriverId);

  // Compute fastest per sector in session
  const sectorMin = (key: 'duration_s1_ms' | 'duration_s2_ms' | 'duration_s3_ms') => {
    const vals = lapTimes
      .filter(l => l.session_id === sessionId)
      .map(l => l[key])
      .filter((v): v is number => v !== null && v !== undefined && v > 0);
    return vals.length ? Math.min(...vals) : null;
  };
  const sessionFastest = {
    s1: sectorMin('duration_s1_ms'),
    s2: sectorMin('duration_s2_ms'),
    s3: sectorMin('duration_s3_ms'),
  };

  // Compute personal best per sector for selected driver
  const driverBest = {
    s1: driverLapTimes
      .map(l => l.duration_s1_ms)
      .filter((v): v is number => v !== null && v !== undefined && v > 0)
      .reduce<number | null>((min, v) => (min === null ? v : Math.min(min, v)), null),
    s2: driverLapTimes
      .map(l => l.duration_s2_ms)
      .filter((v): v is number => v !== null && v !== undefined && v > 0)
      .reduce<number | null>((min, v) => (min === null ? v : Math.min(min, v)), null),
    s3: driverLapTimes
      .map(l => l.duration_s3_ms)
      .filter((v): v is number => v !== null && v !== undefined && v > 0)
      .reduce<number | null>((min, v) => (min === null ? v : Math.min(min, v)), null),
  };

  const formatSectorTime = (ms: number | null) => formatLap(ms);

  const sectorColor = (ms: number | null, fastest: number | null, personal: number | null) => {
    if (ms === null || ms === undefined) return 'text-zinc-500';
    if (fastest && ms === fastest) return 'text-purple-500';
    if (personal && ms === personal) return 'text-green-500';
    return 'text-zinc-300';
  };

  const segmentColorClass = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'bg-zinc-800';
    const meaning = segmentMeaning[value];
    const label = meaning?.color_label?.toLowerCase() || '';
    if (label.includes('purple')) return 'bg-purple-500';
    if (label.includes('green')) return 'bg-green-500';
    if (label.includes('yellow')) return 'bg-yellow-500';
    // pitlane or unknown -> default
    return 'bg-zinc-800';
  };

  const renderSegments = (segments: number[] | null | undefined) => {
    if (!segments || segments.length === 0) {
      return <div className="flex gap-1">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-4 w-3 rounded bg-zinc-800" />)}</div>;
    }
    return (
      <div className="flex gap-1">
        {segments.map((val, idx) => (
          <div
            key={idx}
            className={`h-4 w-3 rounded ${segmentColorClass(val)}`}
            title={segmentMeaning[val]?.meaning || undefined}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Driver selector */}
      <div className="flex items-center gap-2">
        <label className="text-zinc-400 text-sm">Driver:</label>
        <select
          value={selectedDriverId || ''}
          onChange={(e) => onSelectDriver(e.target.value || null)}
          className="bg-zinc-900 text-white text-sm px-3 py-2 rounded border border-zinc-800 focus:outline-none"
        >
          {driversForSession.map((d) => (
            <option key={d.driver_id} value={d.driver_id}>
              {d.driver_number ? `${d.driver_number} - ` : ''}{d.driver_name}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm text-zinc-200">
          <thead className="text-xs uppercase text-zinc-500">
            <tr className="border-b border-zinc-800">
              <th className="py-2 px-2 text-left">Lap</th>
              <th className="py-2 px-2 text-left">Lap Time</th>
              <th className="py-2 px-2 text-left">Sector 1</th>
              <th className="py-2 px-2 text-left">Sector 2</th>
              <th className="py-2 px-2 text-left">Sector 3</th>
            </tr>
          </thead>
          <tbody>
            {lapTimesLoading && (
              <tr>
                <td colSpan={5} className="py-6 text-center text-zinc-500">Loading lap times…</td>
              </tr>
            )}
            {!lapTimesLoading && driverLapTimes.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-center text-zinc-500">No lap times available</td>
              </tr>
            )}
            {!lapTimesLoading && driverLapTimes.map((lap) => (
              <tr key={`${lap.driver_id}-${lap.lap_number}`} className="border-b border-zinc-900">
                <td className="py-2 px-2 font-mono text-zinc-400">{lap.lap_number}</td>
                <td className="py-2 px-2 font-mono text-white">{formatLap(lap.lap_duration_ms)}</td>
                {[1,2,3].map((sector) => {
                  const duration = sector === 1 ? lap.duration_s1_ms : sector === 2 ? lap.duration_s2_ms : lap.duration_s3_ms;
                  const fastest = sector === 1 ? sessionFastest.s1 : sector === 2 ? sessionFastest.s2 : sessionFastest.s3;
                  const personal = sector === 1 ? driverBest.s1 : sector === 2 ? driverBest.s2 : driverBest.s3;
                  const segments = sector === 1 ? lap.s1_segments : sector === 2 ? lap.s2_segments : lap.s3_segments;
                  return (
                    <td key={sector} className="py-2 px-2">
                      <div className={`font-mono text-sm ${sectorColor(duration, fastest, personal)}`}>
                        {formatSectorTime(duration)}
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        {renderSegments(segments)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

interface LapPaceTabProps {
  sessionId: string | null;
  lapTimes: LapTimeRow[];
  lapTimesLoading: boolean;
  classification: ClassificationData[];
  selectedDriverId: string | null;
  onSelectDriver: (driverId: string | null) => void;
}

const LapPaceTab = ({
  sessionId,
  lapTimes,
  lapTimesLoading,
  classification,
  selectedDriverId,
  onSelectDriver,
}: LapPaceTabProps) => {
  if (!sessionId) return null;

  const driversForSession = classification.filter(c => c.session_id === sessionId);
  const driverLapTimes = lapTimes
    .filter(l => l.session_id === sessionId && l.driver_id === selectedDriverId && l.lap_duration_ms !== null && l.lap_duration_ms !== undefined)
    .sort((a, b) => a.lap_number - b.lap_number);

  const lapNumbers = driverLapTimes.map(l => l.lap_number);
  const lapDurations = driverLapTimes.map(l => l.lap_duration_ms || 0);

  const minLap = lapNumbers.length ? Math.min(...lapNumbers) : 0;
  const maxLap = lapNumbers.length ? Math.max(...lapNumbers) : 1;
  const minTime = lapDurations.length ? Math.min(...lapDurations) : 0;
  const maxTime = lapDurations.length ? Math.max(...lapDurations) : 1;

  const yMin = minTime * 0.98;
  const yMax = maxTime * 1.02;

  const width = 900;
  const height = 360;
  const margin = { top: 20, right: 20, bottom: 40, left: 60 };
  const xMax = width - margin.left - margin.right;
  const yMaxPx = height - margin.top - margin.bottom;

  const xScale = scaleLinear({
    domain: [minLap || 0, maxLap || 1],
    range: [0, xMax],
    nice: true,
  });

  const yScale = scaleLinear({
    domain: [yMax, yMin || 0], // invert so faster (lower) times are higher
    range: [yMaxPx, 0],
    nice: true,
  });

  const formatLapLabel = (ms: number | null | undefined) => {
    if (ms === null || ms === undefined) return '-';
    const totalSeconds = ms / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toFixed(3).padStart(6, '0')}`;
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Driver selector */}
      <div className="flex items-center gap-2">
        <label className="text-zinc-400 text-sm">Driver:</label>
        <select
          value={selectedDriverId || ''}
          onChange={(e) => onSelectDriver(e.target.value || null)}
          className="bg-zinc-900 text-white text-sm px-3 py-2 rounded border border-zinc-800 focus:outline-none"
        >
          {driversForSession.map((d) => (
            <option key={d.driver_id} value={d.driver_id}>
              {d.driver_number ? `${d.driver_number} - ` : ''}{d.driver_name}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-zinc-900 rounded-corner p-4 overflow-x-auto">
        {lapTimesLoading && (
          <div className="py-6 text-center text-zinc-500">Loading lap pace…</div>
        )}
        {!lapTimesLoading && driverLapTimes.length === 0 && (
          <div className="py-6 text-center text-zinc-500">No lap data available</div>
        )}
        {!lapTimesLoading && driverLapTimes.length > 0 && (
          <svg width={width} height={height} className="min-w-full">
            <Group left={margin.left} top={margin.top}>
              <AxisLeft
                scale={yScale}
                tickFormat={(val) => formatLapLabel(Number(val))}
                stroke="#52525b"
                tickStroke="#52525b"
                tickLabelProps={() => ({
                  fill: '#a1a1aa',
                  fontSize: 10,
                  fontFamily: 'var(--font-mono)',
                  textAnchor: 'end',
                  dx: -6,
                })}
              />
              <AxisBottom
                top={yMaxPx}
                scale={xScale}
                stroke="#52525b"
                tickStroke="#52525b"
                tickLabelProps={() => ({
                  fill: '#a1a1aa',
                  fontSize: 10,
                  fontFamily: 'var(--font-mono)',
                  textAnchor: 'middle',
                  dy: 12,
                })}
              />

              <LinePath
                data={driverLapTimes}
                x={(d) => xScale(d.lap_number) ?? 0}
                y={(d) => yScale(d.lap_duration_ms || 0) ?? 0}
                stroke={driverLapTimes[0]?.color_hex?.startsWith('#') ? driverLapTimes[0].color_hex : '#ffffff'}
                strokeWidth={2}
                strokeOpacity={0.9}
              />
            </Group>
          </svg>
        )}
      </div>
    </div>
  );
};
