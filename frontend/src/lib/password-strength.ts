const PREDICTABLE_PATTERN = /1234|2345|3456|4567|5678|6789|abcd|bcde|cdef|defg|efgh|fghi|ghij|hijk|ijkl|jklm|klmn|lmno|mnop|qwer|asdf|zxcv|password|admin|letmein|welcome/i;

export function passwordStrengthScore(password: string): number {
  if (!password) return 0;

  const length = Array.from(password).length;
  let score = 0;
  if (length >= 8) score += 2;
  if (length >= 12) score += 1;
  if (length >= 16) score += 1;

  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^a-zA-Z0-9]/.test(password)) score += 1;

  const uniqueRatio = new Set(Array.from(password)).size / length;
  if (uniqueRatio >= 0.75) score += 1;
  else if (uniqueRatio < 0.5) score -= 2;
  if (PREDICTABLE_PATTERN.test(password)) score -= 2;

  return Math.max(0, Math.min(10, score));
}

export function passwordStrengthLabel(score: number): string {
  if (score <= 2) return 'Très faible';
  if (score <= 4) return 'Faible';
  if (score <= 6) return 'Moyenne';
  if (score <= 8) return 'Forte';
  return 'Très forte';
}

export function passwordStrengthColor(score: number): string {
  if (score <= 2) return 'bg-red-500';
  if (score <= 4) return 'bg-orange-500';
  if (score <= 6) return 'bg-amber-500';
  if (score <= 8) return 'bg-green-500';
  return 'bg-emerald-600';
}
