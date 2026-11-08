import type { ReactNode } from 'react';

export type ChipKind = '' | 'good' | 'bad' | 'warn' | 'quiet';

export function Chip({ kind = '', children }: { kind?: ChipKind; children: ReactNode }) {
  return <span className={`chip ${kind}`}>{children}</span>;
}
