/**
 * Date Utilities
 */

export const formatDate = (date: string | Date): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString();
};

export const formatDateTime = (date: string | Date): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString();
};

export const formatTime = (date: string | Date): string => {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleTimeString();
};

export const getTimeRangeDuration = (range: '7d' | '30d' | '90d'): number => {
  const days = {
    '7d': 7,
    '30d': 30,
    '90d': 90,
  };
  return days[range] * 24 * 60 * 60; // seconds
};
