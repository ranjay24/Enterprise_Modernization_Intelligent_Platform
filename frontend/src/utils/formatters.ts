export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-US').format(n);
}

export function getScore(val: unknown): number {
  if (typeof val === 'number') return val;
  if (val && typeof val === 'object' && 'score' in val) return (val as { score: number }).score;
  return 0;
}

export function formatConfidence(raw: unknown): number {
  const val = getScore(raw);
  if (val <= 0) return 0;
  return val <= 1 ? Math.round(val * 100) : Math.round(val);
}
