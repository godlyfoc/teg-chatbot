/** Small SVG icons for the chat UI — consistent sizing & alignment */

function sparklePath(cx: number, cy: number, size: number): string {
  const r = size;
  return [
    `M${cx} ${cy - r}`,
    `C${cx + r * 0.2} ${cy - r * 0.35} ${cx + r} ${cy} ${cx + r} ${cy}`,
    `C${cx + r * 0.2} ${cy + r * 0.35} ${cx} ${cy + r} ${cx} ${cy + r}`,
    `C${cx - r * 0.2} ${cy + r * 0.35} ${cx - r} ${cy} ${cx - r} ${cy}`,
    `C${cx - r * 0.2} ${cy - r * 0.35} ${cx} ${cy - r} ${cx} ${cy - r}`,
    "Z",
  ].join(" ");
}

const BULB_BRAIN_RAYS = [
  [32, 5, 32, 9],
  [44, 7, 42.5, 10.5],
  [53, 14, 50.5, 16],
  [58, 24, 54.5, 25],
  [58, 34, 54.5, 33],
  [53, 44, 50.5, 42],
  [19, 7, 21.5, 10.5],
  [10, 14, 13.5, 16],
  [6, 24, 9.5, 25],
  [6, 34, 9.5, 33],
  [10, 44, 13.5, 42],
] as const;

function BulbBrainSvg({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" className={className}>
      <g stroke="#1a1a1a" strokeWidth="1.1" strokeLinecap="round">
        {BULB_BRAIN_RAYS.map(([x1, y1, x2, y2], index) => (
          <line key={index} x1={x1} y1={y1} x2={x2} y2={y2} />
        ))}
      </g>
      <path
        d="M32 9 C22 9 13 18 13 29 C13 35 17 40 22 40 L32 40 Z"
        fill="#F4C430"
        stroke="#1a1a1a"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path
        d="M32 9 C39 9 46 12 50 18 C53 24 52 31 48 36 C45 39 41 40 38 40 L32 40 Z"
        fill="#F4C430"
        stroke="#1a1a1a"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path d="M32 9 L32 40" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M18 17 C20 14 24 13 27 16 C24 19 20 20 18 17 Z" fill="#fff" opacity="0.55" />
      <path
        fill="none"
        stroke="#1a1a1a"
        strokeWidth="1"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M35 16 C39 14 44 16 46 20 M34 22 C38 20 43 23 45 27 M35 28 C39 27 43 30 44 34 M36 33 C40 32 43 35 44 38"
      />
      <rect x="22" y="40" width="20" height="3.2" fill="#bdbdbd" stroke="#1a1a1a" strokeWidth="1" />
      <line x1="22" y1="41.6" x2="42" y2="41.6" stroke="#1a1a1a" strokeWidth="0.7" />
      <rect x="23" y="43.2" width="18" height="2.8" fill="#9e9e9e" stroke="#1a1a1a" strokeWidth="1" />
      <line x1="23" y1="44.6" x2="41" y2="44.6" stroke="#1a1a1a" strokeWidth="0.7" />
      <rect x="24" y="46" width="16" height="2.8" fill="#bdbdbd" stroke="#1a1a1a" strokeWidth="1" />
      <line x1="24" y1="47.4" x2="40" y2="47.4" stroke="#1a1a1a" strokeWidth="0.7" />
      <ellipse cx="32" cy="50.5" rx="2.8" ry="1.4" fill="#1a1a1a" />
    </svg>
  );
}

export function IconTrash() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  );
}

export function IconChevronDown() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}

export function IconSend() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
    </svg>
  );
}

export function IconChat() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2z" />
    </svg>
  );
}

export function IconClose() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

/** Three-star sparkles — chat panel header */
export function IconSparkles() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="icon-sparkles">
      <path d={sparklePath(17.5, 16.5, 5.5)} />
      <path d={sparklePath(8.5, 13.5, 4)} />
      <path d={sparklePath(13, 6.5, 3)} />
    </svg>
  );
}

/** AI bulb/brain — assistant message indicator */
export function IconAiBulb() {
  return <BulbBrainSvg className="icon-ai-bulb" />;
}
