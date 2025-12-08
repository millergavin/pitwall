import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { MeetingCard, type MeetingCardData } from '../components/MeetingCard';
import { api } from '../api/client';
import { FontAwesomeIcon } from '../lib/fontawesome';
import { faArrowDown, faArrowUp } from '@fortawesome/free-solid-svg-icons';

export const GrandPrix = () => {
  const [meetings, setMeetings] = useState<MeetingCardData[]>([]);
  const [coverImagesMap, setCoverImagesMap] = useState<Record<string, string>>({});
  const [availableSeasons, setAvailableSeasons] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);
  const [sortAscending, setSortAscending] = useState(true);
  const navigate = useNavigate();

  // Sort meetings by round number
  const sortedMeetings = useMemo(() => {
    return [...meetings].sort((a, b) => {
      return sortAscending 
        ? a.round_number - b.round_number 
        : b.round_number - a.round_number;
    });
  }, [meetings, sortAscending]);

  // Fetch available seasons on mount
  useEffect(() => {
    const fetchSeasons = async () => {
      try {
        const seasons = await api.seasons();
        setAvailableSeasons(seasons);
        
        if (seasons.length > 0 && selectedSeason === null) {
          const currentYear = new Date().getFullYear();
          // Default to current year if available, otherwise fall back to most recent
          if (seasons.includes(currentYear)) {
            setSelectedSeason(currentYear);
          } else {
            setSelectedSeason(seasons[0]);
          }
        }
      } catch (err) {
        console.error('Failed to fetch seasons:', err);
        // Fallback to current year if seasons fetch fails
        setSelectedSeason(new Date().getFullYear());
      }
    };
    fetchSeasons();
  }, []);

  // Fetch meetings and cover images when season changes
  useEffect(() => {
    if (selectedSeason === null) return;
    
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch meetings for the selected season
        const meetingsData = await api.meetings(selectedSeason);
        setMeetings(meetingsData);

        // Fetch cover images for each circuit
        try {
          const allImages = await api.images({});
          const coverMap: Record<string, string> = {};
          
          // Group images by circuit_id, prioritize is_cover = true
          for (const img of allImages) {
            if (img.circuit_id && img.file_path) {
              // Only set if not already set, or if this is a cover image
              if (!coverMap[img.circuit_id] || img.is_cover) {
                coverMap[img.circuit_id] = `/assets/circuit_image/${img.file_path}`;
              }
            }
          }
          
          setCoverImagesMap(coverMap);
        } catch {
          // Ignore image fetch errors
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load Grand Prix data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedSeason]);

  const handleMeetingClick = (meetingId: string) => {
    navigate(`/grand-prix/${meetingId}`);
  };

  return (
    <PageLayout pageTitle="Grand Prix" sidebar={<NavSidebar />}>
      <div className="flex flex-col h-full">
        {/* Season selector and sort control */}
        <div className="mb-6 flex items-center gap-4">
          <label className="text-white f1-display-regular text-lg">Season:</label>
          <select
            value={selectedSeason ?? ''}
            onChange={(e) => setSelectedSeason(Number(e.target.value))}
            className="bg-zinc-800 text-white px-4 py-2 rounded-corner f1-display-regular focus:outline-none focus:ring-2 focus:ring-f1-red"
            disabled={availableSeasons.length === 0}
          >
            {availableSeasons.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
          
          {/* Sort toggle button */}
          <button
            onClick={() => setSortAscending(!sortAscending)}
            className="flex items-center gap-2 bg-zinc-800 text-white px-4 py-2 rounded-corner f1-display-regular hover:bg-zinc-700 transition-colors focus:outline-none focus:ring-2 focus:ring-f1-red"
            title={sortAscending ? 'Sort by round (ascending)' : 'Sort by round (descending)'}
          >
            <span className="text-sm uppercase">Sort</span>
            <FontAwesomeIcon 
              icon={sortAscending ? faArrowDown : faArrowUp} 
              className="text-sm"
            />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-f1-red"></div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-f1-red text-lg">{error}</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-6">
              {sortedMeetings.map((meeting) => (
                <MeetingCard
                  key={meeting.meeting_id}
                  meeting={meeting}
                  coverImageUrl={coverImagesMap[meeting.circuit_id]}
                  onClick={() => handleMeetingClick(meeting.meeting_id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
};

