/**
 * Brand-aligned SVG illustrations for empty states.
 * Pirsch-flavoured: simple geometric forms, sunbeam yellow + leaf green
 * accents on an off-white surface. Stroke-based, soft rounded ends.
 */

interface IllustrationProps {
  className?: string;
  width?: number;
  height?: number;
}

export function GalaxyIllustration({
  className,
  width = 220,
  height = 180,
}: IllustrationProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 220 180"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Universo vacío"
      className={className}
    >
      <ellipse cx="110" cy="90" rx="90" ry="22" stroke="#0a0a0a" strokeOpacity="0.08" strokeWidth="1.5" />
      <ellipse cx="110" cy="90" rx="65" ry="14" stroke="#0a0a0a" strokeOpacity="0.06" strokeWidth="1.5" />
      <circle cx="110" cy="90" r="14" fill="#ffda6e" />
      <circle cx="110" cy="90" r="14" stroke="#0a0a0a" strokeOpacity="0.12" strokeWidth="1.5" />
      <circle cx="40" cy="70" r="4" fill="#6ece9d" />
      <circle cx="180" cy="105" r="3" fill="#6ece9d" />
      <circle cx="160" cy="55" r="2" fill="#0a0a0a" fillOpacity="0.18" />
      <circle cx="60" cy="120" r="2.5" fill="#0a0a0a" fillOpacity="0.22" />
      <circle cx="195" cy="80" r="1.5" fill="#0a0a0a" fillOpacity="0.3" />
      <circle cx="25" cy="100" r="1.5" fill="#0a0a0a" fillOpacity="0.3" />
      <path
        d="M 102 76 L 100 70 L 96 72"
        stroke="#0a0a0a"
        strokeOpacity="0.35"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function PaperPlaneIllustration({
  className,
  width = 220,
  height = 180,
}: IllustrationProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 220 180"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Sin documentos"
      className={className}
    >
      <path
        d="M 30 130 L 170 60 L 150 145 L 110 105 Z"
        fill="#ffda6e"
      />
      <path
        d="M 30 130 L 170 60 L 150 145 L 110 105 Z"
        stroke="#0a0a0a"
        strokeOpacity="0.5"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M 30 130 L 110 105"
        stroke="#0a0a0a"
        strokeOpacity="0.4"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M 110 105 L 130 90"
        stroke="#0a0a0a"
        strokeOpacity="0.3"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M 50 95 Q 75 100 100 80"
        stroke="#6ece9d"
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray="2 4"
        fill="none"
      />
      <circle cx="190" cy="50" r="3" fill="#6ece9d" />
    </svg>
  );
}

export function NotebookIllustration({
  className,
  width = 220,
  height = 180,
}: IllustrationProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 220 180"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Sin notas"
      className={className}
    >
      <rect
        x="60"
        y="35"
        width="100"
        height="120"
        rx="12"
        fill="#f8f5ed"
        stroke="#0a0a0a"
        strokeOpacity="0.4"
        strokeWidth="1.5"
      />
      <line x1="75" y1="60" x2="145" y2="60" stroke="#0a0a0a" strokeOpacity="0.15" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="75" y1="75" x2="135" y2="75" stroke="#0a0a0a" strokeOpacity="0.15" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="75" y1="90" x2="140" y2="90" stroke="#0a0a0a" strokeOpacity="0.15" strokeWidth="1.5" strokeLinecap="round" />
      <rect x="75" y="105" width="36" height="22" rx="6" fill="#ffda6e" />
      <line x1="115" y1="115" x2="145" y2="115" stroke="#0a0a0a" strokeOpacity="0.15" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="55" y1="55" x2="55" y2="135" stroke="#6ece9d" strokeWidth="3" strokeLinecap="round" />
      <circle cx="190" cy="60" r="3" fill="#6ece9d" />
      <circle cx="40" cy="160" r="2" fill="#0a0a0a" fillOpacity="0.3" />
    </svg>
  );
}

export function BellQuietIllustration({
  className,
  width = 180,
  height = 140,
}: IllustrationProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 180 140"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Sin recordatorios"
      className={className}
    >
      <path
        d="M 90 30 C 70 30 60 45 60 65 L 60 80 L 50 95 L 130 95 L 120 80 L 120 65 C 120 45 110 30 90 30 Z"
        fill="#6ece9d"
        fillOpacity="0.18"
        stroke="#0a0a0a"
        strokeOpacity="0.4"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M 82 95 C 82 100 85 105 90 105 C 95 105 98 100 98 95"
        stroke="#0a0a0a"
        strokeOpacity="0.4"
        strokeWidth="1.5"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="90" cy="25" r="3" fill="#ffda6e" />
      <path d="M 50 110 Q 90 130 130 110" stroke="#6ece9d" strokeWidth="2" strokeLinecap="round" fill="none" />
    </svg>
  );
}
