import { useState } from 'react';

export interface MeetingCardData {
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

interface MeetingCardProps {
  meeting: MeetingCardData;
  coverImageUrl?: string | null;
  onClick?: () => void;
}

export const MeetingCard = ({ meeting, coverImageUrl, onClick }: MeetingCardProps) => {
  const [imageError, setImageError] = useState(false);

  // Format dates
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const startDate = formatDate(meeting.date_start);
  const endDate = formatDate(meeting.date_end);

  return (
    <div
      onClick={onClick}
      className="relative overflow-hidden rounded-corner cursor-pointer group transition-transform hover:scale-[1.02] active:scale-[0.98]"
      style={{
        aspectRatio: '16 / 9',
        backgroundColor: '#1a1a1a',
      }}
    >
      {/* Circuit cover image */}
      {coverImageUrl && !imageError ? (
        <div className="absolute inset-0">
          <img
            src={coverImageUrl}
            alt={meeting.circuit_name}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
          {/* Dark gradient overlay for text legibility */}
          <div
            className="absolute inset-0"
            style={{
              background: 'linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.6) 40%, rgba(0,0,0,0.3) 70%, rgba(0,0,0,0.1) 100%)',
            }}
          />
        </div>
      ) : (
        <div className="absolute inset-0 bg-zinc-900" />
      )}

      {/* Content Container */}
      <div className="relative h-full flex flex-col justify-between p-6">
        {/* Top section - Round number and flag */}
        <div className="flex justify-between items-start">
          {/* Round number badge */}
          <div className="bg-f1-red text-white px-3 py-1 rounded text-xs f1-display-bold">
            {meeting.round_number === 0 ? 'TESTING' : `ROUND ${meeting.round_number}`}
          </div>

          {/* Flag */}
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

        {/* Bottom section - Meeting info */}
        <div className="z-10">
          {/* Date range */}
          <div className="text-white text-base f1-display-bold mb-2 opacity-70">
            {startDate} – {endDate}
          </div>
          
          {/* Meeting name */}
          <h2
            className="text-white f1-display-bold text-3xl leading-tight uppercase mb-1"
            style={{
              textShadow: '0 2px 8px rgba(0, 0, 0, 0.8)',
            }}
          >
            {meeting.meeting_short_name}
          </h2>
          
          {/* Circuit name */}
          <h3
            className="text-zinc-300 f1-display-regular text-lg leading-tight"
            style={{
              textShadow: '0 2px 4px rgba(0, 0, 0, 0.8)',
            }}
          >
            {meeting.circuit_name}
          </h3>
        </div>
      </div>

      {/* Hover effect overlay */}
      <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none" />
    </div>
  );
};

