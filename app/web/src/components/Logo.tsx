// The Aemon mark: a lowercase a whose bowl is an open eye. Inline, so it shows before sign-in too
// (the same drawing as public/brand/aemon/logo.svg).
export function Logo({ size = 28, className = 'logo-mark' }: { size?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <rect width="64" height="64" rx="16" fill="#14161b" />
      <circle cx="29" cy="35" r="13.5" fill="none" stroke="#fff" strokeWidth="6.5" />
      <rect x="39.5" y="19" width="6.5" height="30" rx="3.25" fill="#fff" />
      <circle cx="32" cy="32" r="4.2" fill="#7c9bff" />
    </svg>
  );
}
