'use client';

import { Badge } from '@/components/ui/badge';
import { ShieldAlert, Scale, Ban, CheckCircle2, FileWarning, BookOpen } from 'lucide-react';

export interface RuleBadgeMeta {
  label: string;
  className: string;
  Icon: typeof Scale;
}

const RULE_TYPE_MAP: Record<string, RuleBadgeMeta> = {
  mandatory: {
    label: 'Obligation impérative',
    className: 'bg-blue-50 text-blue-800 border-blue-200',
    Icon: CheckCircle2,
  },
  prohibition: {
    label: 'Interdiction',
    className: 'bg-rose-50 text-rose-800 border-rose-200',
    Icon: Ban,
  },
  conditional: {
    label: 'Condition / Autorisation',
    className: 'bg-amber-50 text-amber-800 border-amber-200',
    Icon: FileWarning,
  },
  sanction: {
    label: 'Disposition pénale / Sanction',
    className: 'bg-red-50 text-red-800 border-red-200',
    Icon: ShieldAlert,
  },
  recommendation: {
    label: 'Recommandation',
    className: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    Icon: BookOpen,
  },
  definition: {
    label: 'Définition',
    className: 'bg-slate-100 text-slate-700 border-slate-200',
    Icon: Scale,
  },
};

export function getRuleTypeMeta(ruleType?: string | null): RuleBadgeMeta | null {
  if (!ruleType) return null;
  return RULE_TYPE_MAP[ruleType.toLowerCase()] || null;
}

export function RuleTypeBadge({ ruleType }: { ruleType?: string | null }) {
  const meta = getRuleTypeMeta(ruleType);
  if (!meta) return null;
  const Icon = meta.Icon;
  return (
    <Badge variant="outline" className={`text-[11px] font-medium gap-1 ${meta.className}`}>
      <Icon className="w-3 h-3 shrink-0" />
      <span>{meta.label}</span>
    </Badge>
  );
}

export function SanctionBadge({ hasSanction }: { hasSanction?: boolean }) {
  if (!hasSanction) return null;
  return (
    <Badge variant="outline" className="text-[11px] font-semibold gap-1 bg-red-50 text-red-700 border-red-200">
      <ShieldAlert className="w-3 h-3 shrink-0" />
      <span>Sanction prévue</span>
    </Badge>
  );
}

export function JurisdictionBadge({ jurisdiction }: { jurisdiction: string }) {
  return (
    <Badge variant="outline" className="text-[11px] font-mono font-semibold bg-sovereign-50 text-sovereign-700 border-sovereign-200">
      {jurisdiction}
    </Badge>
  );
}
