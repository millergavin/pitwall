import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { Button } from '../components/Button';
import { FontAwesomeIcon } from '../lib/fontawesome';
import { faArrowLeft, faGears, faStopwatch, faFlagCheckered } from '@fortawesome/free-solid-svg-icons';
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

export const MeetingDetails = () => {
  const { meetingId } = useParams<{ meetingId: string }>();
  const [meeting, setMeeting] = useState<MeetingData | null>(null);
  const [sessions, setSessions] = useState<SessionData[]>([]);
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
        setSessions(sessionsData);

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

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

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

  const getSessionIcon = (sessionType: string) => {
    switch (sessionType) {
      case 'p1':
      case 'p2':
      case 'p3':
        return { icon: faGears, bgColor: 'bg-sky-600' };
      case 'sprint_quali':
        return { icon: faStopwatch, bgColor: 'bg-purple-600' };
      case 'quali':
        return { icon: faStopwatch, bgColor: 'bg-purple-600' };
      case 'sprint':
      case 'race':
        return { icon: faFlagCheckered, bgColor: 'bg-black' };
      default:
        return { icon: faGears, bgColor: 'bg-zinc-600' };
    }
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

  const handleSessionClick = (sessionId: string) => {
    navigate(`/sessions/${sessionId}`);
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

  return (
    <PageLayout 
      pageTitle={`${meeting.season} ${meeting.meeting_short_name}`}
      sidebar={<NavSidebar />}
    >
      <div className="flex flex-col h-full gap-6">
        {/* Back button */}
        <div>
          <Button 
            variant="text" 
            size="sm"
            icon={faArrowLeft}
            onClick={() => navigate('/grand-prix')}
          >
            Back to Grand Prix
          </Button>
        </div>

        {/* Hero Section */}
        <div 
          className="relative rounded-corner overflow-hidden"
          style={{ height: '280px' }}
        >
          {/* Cover image */}
          {coverImageUrl ? (
            <img
              src={coverImageUrl}
              alt={meeting.circuit_name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full bg-black" />
          )}
          
          {/* Dark gradient overlay */}
          <div
            className="absolute inset-0"
            style={{
              background: 'linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 40%, rgba(0,0,0,0.3) 70%, rgba(0,0,0,0.0) 100%)',
            }}
          />

          {/* Content */}
          <div className="absolute inset-0 flex flex-col justify-end p-8">
            <div className="flex items-end justify-between">
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <div className="bg-f1-red text-white px-3 py-1 rounded text-sm f1-display-bold">
                    ROUND {meeting.round_number}
                  </div>
                  {meeting.flag_url && (
                    <div className="w-10 h-10 rounded-full overflow-hidden shadow-lg flex-shrink-0">
                      <img
                        src={meeting.flag_url}
                        alt={meeting.country_name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}
                </div>
                <h1
                  className="text-white f1-display-bold text-5xl leading-tight uppercase mb-2"
                  style={{
                    textShadow: '0 2px 12px rgba(0, 0, 0, 0.9)',
                  }}
                >
                  {meeting.meeting_short_name}
                </h1>
                <h2
                  className="text-zinc-300 f1-display-regular text-2xl leading-tight"
                  style={{
                    textShadow: '0 2px 8px rgba(0, 0, 0, 0.9)',
                  }}
                >
                  {meeting.circuit_name}
                </h2>
              </div>
            </div>
          </div>
        </div>

        {/* Meeting Details */}
        <div className="bg-black rounded-corner p-4 lg:p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
            <div>
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular mb-1">Circuit</div>
              <button
                onClick={() => navigate(`/circuits/${meeting.circuit_id}`)}
                className="text-white f1-display-bold text-base lg:text-lg hover:text-f1-red transition-colors text-left"
              >
                {getCircuitDisplayName()}
              </button>
            </div>
            <div>
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular mb-1">Location</div>
              <div className="text-white f1-display-bold text-base lg:text-lg">{meeting.location}</div>
            </div>
            <div>
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular mb-1">Country</div>
              <div className="text-white f1-display-bold text-base lg:text-lg">{meeting.country_name}</div>
            </div>
            <div>
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular mb-1">Date</div>
              <div className="text-white f1-display-bold text-base lg:text-lg">
                {new Date(meeting.date_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - {new Date(meeting.date_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </div>
            </div>
          </div>
        </div>

        {/* Sessions List */}
        <div className="flex-1">
          <h2 className="text-white f1-display-bold text-xl lg:text-2xl mb-3 lg:mb-4">Sessions</h2>
          <div className="grid grid-cols-1 gap-3 lg:gap-4">
            {sessions.map((session) => (
              <div
                key={session.session_id}
                onClick={() => handleSessionClick(session.session_id)}
                className="bg-black rounded-corner p-4 lg:p-6 cursor-pointer hover:bg-zinc-800 transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 lg:gap-4 flex-1">
                    {/* Session icon */}
                    <div className={`w-10 h-10 lg:w-12 lg:h-12 rounded-full ${getSessionIcon(session.session_type).bgColor} flex items-center justify-center flex-shrink-0`}>
                      <FontAwesomeIcon 
                        icon={getSessionIcon(session.session_type).icon} 
                        className="text-white text-base lg:text-lg"
                      />
                    </div>
                    
                    {/* Session info */}
                    <div className="flex-1 min-w-0">
                      <h3 className="text-white f1-display-bold text-lg lg:text-xl mb-1 truncate">
                        {getSessionDisplayName(session.session_type)}
                      </h3>
                      <p className="text-zinc-400 f1-display-regular text-xs lg:text-sm truncate">
                        {formatDate(session.start_time)}
                      </p>
                    </div>
                  </div>

                  {/* Winner if available */}
                  {session.winner_driver_name && (
                    <div className="text-right hidden md:block flex-shrink-0 ml-4">
                      <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular mb-1">Winner</div>
                      <div className="text-white f1-display-bold text-base lg:text-lg">
                        {session.winner_driver_name}
                      </div>
                    </div>
                  )}

                  {/* Arrow */}
                  <div className="text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0 ml-2">
                    <svg className="w-5 h-5 lg:w-6 lg:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

