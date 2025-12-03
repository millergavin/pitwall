import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import type { IconDefinition } from '@fortawesome/fontawesome-svg-core';

interface IconProps {
  icon: IconDefinition;
  className?: string;
}

export const Icon = ({ icon, className }: IconProps) => {
  return <FontAwesomeIcon icon={icon} className={className} />;
};

