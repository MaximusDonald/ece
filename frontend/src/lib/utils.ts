import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date, options?: Intl.DateTimeFormatOptions): string {
  const d = new Date(date);
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    ...options,
  });
}

export function formatDateTime(date: string | Date): string {
  const d = new Date(date);
  return d.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getRiskBadgeClass(riskLevel: string): string {
  const classes: Record<string, string> = {
    critique: 'badge-critique',
    eleve: 'badge-eleve',
    modere: 'badge-modere',
    a_surveiller: 'badge-a_surveiller',
    conforme: 'badge-conforme',
  };
  return classes[riskLevel] || 'badge';
}

export function getConfidenceBadgeClass(confidence: string): string {
  const classes: Record<string, string> = {
    high: 'badge-high',
    medium: 'badge-medium',
    low: 'badge-low',
  };
  return classes[confidence] || 'badge';
}

export function getRiskEmoji(riskLevel: string): string {
  const emojis: Record<string, string> = {
    critique: '🔴',
    eleve: '🟠',
    modere: '🟡',
    a_surveiller: '🔵',
    conforme: '🟢',
  };
  return emojis[riskLevel] || '⚪';
}

export function getConfidenceEmoji(confidence: string): string {
  const emojis: Record<string, string> = {
    high: '🟢',
    medium: '🟡',
    low: '🔴',
  };
  return emojis[confidence] || '⚪';
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}