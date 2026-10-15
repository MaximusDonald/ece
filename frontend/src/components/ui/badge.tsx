'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-sovereign-500 focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-sovereign-100 text-sovereign-700 hover:bg-sovereign-200',
        secondary: 'border-transparent bg-slate-100 text-slate-700 hover:bg-slate-200',
        destructive: 'border-transparent bg-danger-100 text-danger-700 hover:bg-danger-200',
        warning: 'border-transparent bg-warning-50 text-warning-700',
        outline: 'text-slate-700',
        critique: 'border-transparent bg-danger-50 text-danger-700',
        eleve: 'border-transparent bg-warning-50 text-warning-700',
        modere: 'border-transparent bg-warning-50 text-warning-700',
        a_surveiller: 'border-transparent bg-sovereign-100 text-sovereign-700',
        conforme: 'border-transparent bg-success-50 text-success-700',
        high: 'border-transparent bg-success-50 text-success-700',
        medium: 'border-transparent bg-warning-50 text-warning-700',
        low: 'border-transparent bg-danger-50 text-danger-700',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

type KnownBadgeVariant = VariantProps<typeof badgeVariants>['variant'];
const knownBadgeVariants = [
  'default', 'secondary', 'destructive', 'outline', 'critique', 'eleve',
  'modere', 'a_surveiller', 'conforme', 'high', 'medium', 'low', 'warning',
];

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: KnownBadgeVariant | (string & {});
}

function Badge({ className, variant, ...props }: BadgeProps) {
  const knownVariant = variant && knownBadgeVariants.includes(variant)
    ? variant as KnownBadgeVariant
    : 'default';
  return <div className={cn(badgeVariants({ variant: knownVariant }), className)} {...props} />;
}

export { Badge, badgeVariants };
