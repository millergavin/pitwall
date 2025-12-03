import { IconButton } from './IconButton';
import { Tooltip } from './Tooltip';
import { faCircle } from '@fortawesome/free-solid-svg-icons';

type ApiStatus = 'connected' | 'disconnected' | 'error' | 'warning';

interface ApiStatusIndicatorProps {
  status?: ApiStatus;
}

export const ApiStatusIndicator = ({ status = 'connected' }: ApiStatusIndicatorProps) => {
  const statusConfig = {
    connected: {
      color: 'text-green-500', // Green
      label: 'API Connected',
    },
    disconnected: {
      color: 'text-gray-500', // Gray
      label: 'API Disconnected',
    },
    warning: {
      color: 'text-amber-500', // Amber
      label: 'API Warning',
    },
    error: {
      color: 'text-f1-red', // Red
      label: 'API Error',
    },
  };

  const config = statusConfig[status];

  return (
    <Tooltip content={config.label} position="bottom">
      <IconButton
        size="sm"
        variant="text"
        icon={faCircle}
        aria-label={config.label}
        iconClassName={config.color}
      />
    </Tooltip>
  );
};

