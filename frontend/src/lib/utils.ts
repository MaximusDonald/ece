import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  const maybeError = error as {
    response?: { status?: number; data?: { detail?: unknown; message?: unknown } };
    message?: string;
  };
  const detail = maybeError?.response?.data?.detail ?? maybeError?.response?.data?.message;
  if (maybeError?.response?.status === 401) return 'Le serveur n’a pas authentifié cette requête. Reconnectez-vous puis réessayez.';
  if (maybeError?.response?.status === 403) return 'Vous n’avez pas les droits nécessaires pour effectuer cette action.';
  if (maybeError?.response?.status === 404) return 'La ressource demandée est introuvable.';
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => typeof item?.msg === 'string' ? item.msg : null)
      .filter(Boolean);
    if (messages.length) return messages.join(' ');
  }
  if (!maybeError?.response && maybeError?.message === 'Network Error') {
    return 'Le serveur est injoignable. Vérifiez votre connexion puis réessayez.';
  }
  return fallback;
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

export function formatSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return 'Taille inconnue';
  if (bytes < 1024) return `${bytes} o`;
  const units = ['Ko', 'Mo', 'Go', 'To'];
  let size = bytes / 1024;
  let unit = units[0];
  for (let index = 0; size >= 1024 && index < units.length - 1; index += 1) {
    size /= 1024;
    unit = units[index + 1];
  }
  return `${size.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} ${unit}`;
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
