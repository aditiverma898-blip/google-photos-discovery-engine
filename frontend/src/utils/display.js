export const formatNumber = value => Number(value || 0).toLocaleString();
export const formatPercent = (part, whole) => whole ? `${Math.round((part / whole) * 100)}%` : '—';
export const evidenceUrl = filters => `/evidence?${new URLSearchParams(Object.entries(filters).filter(([, value]) => value !== undefined && value !== null && value !== '').map(([key, value]) => [key, String(value)])).toString()}`;
