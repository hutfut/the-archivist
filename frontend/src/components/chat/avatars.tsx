const SIZES = { sm: 32, md: 48, lg: 64 } as const;
type AvatarSize = keyof typeof SIZES;

export function CaretakerAvatar({ size = "md" }: { size?: AvatarSize }) {
  const px = SIZES[size];
  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="shrink-0"
    >
      <circle cx="32" cy="32" r="31" fill="url(#caretaker-bg)" stroke="var(--color-border-gold)" strokeWidth="1" />
      {/* Open tome / grimoire */}
      <g transform="translate(14, 16)">
        {/* Left page */}
        <path
          d="M18 2C13 2 8 3.5 4 6V30C8 27.5 13 26 18 26V2Z"
          fill="var(--color-accent-gold)"
          opacity="0.85"
        />
        {/* Right page */}
        <path
          d="M18 2C23 2 28 3.5 32 6V30C28 27.5 23 26 18 26V2Z"
          fill="var(--color-accent-gold-bright)"
          opacity="0.7"
        />
        {/* Spine */}
        <line x1="18" y1="2" x2="18" y2="26" stroke="var(--color-accent-crimson)" strokeWidth="1.5" />
        {/* Text lines on left page */}
        <line x1="7" y1="10" x2="15" y2="10" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
        <line x1="7" y1="14" x2="14" y2="14" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
        <line x1="7" y1="18" x2="15" y2="18" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
        {/* Text lines on right page */}
        <line x1="21" y1="10" x2="29" y2="10" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
        <line x1="21" y1="14" x2="28" y2="14" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
        <line x1="21" y1="18" x2="29" y2="18" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
      </g>
      <defs>
        <radialGradient id="caretaker-bg" cx="0.3" cy="0.3" r="0.8">
          <stop offset="0%" stopColor="rgba(200,170,110,0.2)" />
          <stop offset="100%" stopColor="rgba(139,37,0,0.15)" />
        </radialGradient>
      </defs>
    </svg>
  );
}

export function UserAvatar({ size = "md" }: { size?: AvatarSize }) {
  const px = SIZES[size];
  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="shrink-0"
    >
      <circle cx="32" cy="32" r="31" fill="url(#user-bg)" stroke="var(--color-border)" strokeWidth="1" />
      {/* Compass rose */}
      <g transform="translate(32, 32)">
        {/* Cardinal points */}
        <polygon points="0,-16 3,-4 -3,-4" fill="var(--color-accent-blue)" /> {/* N */}
        <polygon points="0,16 3,4 -3,4" fill="var(--color-accent-blue)" opacity="0.7" /> {/* S */}
        <polygon points="16,0 4,3 4,-3" fill="var(--color-accent-blue)" opacity="0.7" /> {/* E */}
        <polygon points="-16,0 -4,3 -4,-3" fill="var(--color-accent-blue)" opacity="0.7" /> {/* W */}
        {/* Intercardinal points */}
        <polygon points="10,-10 2,-2 5,-1" fill="var(--color-accent-blue)" opacity="0.4" />
        <polygon points="10,10 2,2 5,1" fill="var(--color-accent-blue)" opacity="0.4" />
        <polygon points="-10,10 -2,2 -5,1" fill="var(--color-accent-blue)" opacity="0.4" />
        <polygon points="-10,-10 -2,-2 -5,-1" fill="var(--color-accent-blue)" opacity="0.4" />
        {/* Center circle */}
        <circle cx="0" cy="0" r="2.5" fill="var(--color-accent-blue)" />
      </g>
      <defs>
        <radialGradient id="user-bg" cx="0.3" cy="0.3" r="0.8">
          <stop offset="0%" stopColor="rgba(74,127,181,0.15)" />
          <stop offset="100%" stopColor="rgba(74,127,181,0.05)" />
        </radialGradient>
      </defs>
    </svg>
  );
}
