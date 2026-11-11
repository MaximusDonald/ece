'use client';

import { useParams, useSearchParams } from 'next/navigation';
import { useReportDiff, useReportVersion } from '@/hooks/useApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { cn, formatDateTime, getRiskBadgeClass, getConfidenceBadgeClass } from '@/lib/utils';
import { ChevronLeft, ChevronRight, Search, Download, FileText, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import * as Diff from 'diff';

interface DiffLine {
  type: 'added' | 'removed' | 'unchanged' | 'modified';
  content: string;
  line_number_old: number | null;
  line_number_new: number | null;
}

export default function ReportDiffPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const versionId = params.version as string;
  const projectId = params.id as string;
  const compareWith = searchParams.get('compare_with') || searchParams.get('compare') || '';
  const reportType = (searchParams.get('report_type') as 'report1' | 'report2') || 'report1';

  const { data: diffData } = useReportDiff(versionId, compareWith, reportType);
  const { data: versionOld } = useReportVersion(compareWith);
  const { data: versionNew } = useReportVersion(versionId);

  const [viewMode, setViewMode] = useState<'unified' | 'split'>('unified');
  const [showOnlyChanges, setShowOnlyChanges] = useState(false);

  if (!diffData) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
      </div>
    );
  }

  const filteredLines = showOnlyChanges
    ? diffData.diff_lines.filter((l: DiffLine) => l.type !== 'unchanged')
    : diffData.diff_lines;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href={`/dashboard/projects/${projectId}`} className="text-sm text-slate-500 hover:underline">
            ← Projet
          </Link>
          <Link href={`/dashboard/projects/${projectId}/reports/${versionId}`} className="text-sm text-slate-500 hover:underline">
            ← Rapport v{versionNew?.version}
          </Link>
          <h1 className="page-title">Comparaison de versions</h1>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">{reportType === 'report1' ? 'Rapport 1 : Constats' : 'Rapport 2 : Synthèse'}</Badge>
        </div>
      </div>

      {/* Version Info */}
      <Card>
        <CardContent className="p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="outline">v{versionOld?.version || 'ancienne'}</Badge>
                <span className="text-sm text-slate-500">{versionOld ? formatDateTime(versionOld.created_at) : ''}</span>
              </div>
              <p className="font-medium">Score: {versionOld?.global_score || 0}/100</p>
              <p className="text-sm text-slate-500">Confiance: {versionOld?.confidence_global || '—'}</p>
            </div>
            <div className="p-4 bg-sovereign-50 rounded-lg border border-sovereign-200">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="default">v{versionNew?.version || 'nouvelle'}</Badge>
                <span className="text-sm text-slate-500">{versionNew ? formatDateTime(versionNew.created_at) : ''}</span>
              </div>
              <p className="font-medium">Score: {versionNew?.global_score || 0}/100</p>
              <p className="text-sm text-slate-500">Confiance: {versionNew?.confidence_global || '—'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-wrap gap-4">
            <Badge variant="destructive">Supprimés: {diffData.summary.removed || 0}</Badge>
            <Badge variant="default">Ajoutés: {diffData.summary.added || 0}</Badge>
            <Badge variant="warning">Modifiés: {diffData.summary.modified || 0}</Badge>
            <Badge variant="secondary">Inchangés: {diffData.summary.unchanged || 0}</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Controls */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Button
                variant={viewMode === 'unified' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('unified')}
              >
                Vue unifiée
              </Button>
              <Button
                variant={viewMode === 'split' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('split')}
              >
                Vue côte à côte
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showOnlyChanges}
                  onChange={(e) => setShowOnlyChanges(e.target.checked)}
                  className="h-4 w-4 text-sovereign-500 border-slate-300 rounded"
                />
                <span className="text-sm">Masquer les lignes inchangées</span>
              </label>
            </div>
            <div className="flex-1" />
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link href={`/api/reports/${versionId}/export?format=pdf&type=${reportType}&diff=true&compare=${compareWith}`} target="_blank">
                  <Download className="h-4 w-4 mr-2" />
                  Exporter diff (PDF)
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Diff View */}
      <Card>
        <CardContent className="p-0">
          <div className={cn('font-mono text-sm', viewMode === 'split' ? 'grid grid-cols-2' : '')}>
            {viewMode === 'unified' ? (
              <UnifiedDiffView lines={filteredLines} />
            ) : (
              <SplitDiffView lines={filteredLines} />
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function UnifiedDiffView({ lines }: { lines: DiffLine[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="w-12 text-right p-2 text-slate-400">Ancien</th>
            <th className="w-12 text-right p-2 text-slate-400">Nouveau</th>
            <th className="text-left p-2 text-slate-400">Contenu</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => (
            <tr key={index} className={cn(
              'border-b border-slate-100',
              line.type === 'added' && 'bg-success-50',
              line.type === 'removed' && 'bg-danger-50',
              line.type === 'modified' && 'bg-warning-50',
            )}>
              <td className="w-12 text-right p-2 text-slate-400 select-none">
                {line.line_number_old !== null ? line.line_number_old : ''}
              </td>
              <td className="w-12 text-right p-2 text-slate-400 select-none">
                {line.line_number_new !== null ? line.line_number_new : ''}
              </td>
              <td className={cn('p-2', line.type === 'added' && 'text-success-700', line.type === 'removed' && 'text-danger-700')}>
                <span className={cn(
                  'inline-flex w-full',
                  line.type === 'added' && 'bg-success-100',
                  line.type === 'removed' && 'bg-danger-100',
                  line.type === 'modified' && 'bg-warning-100',
                )}>
                  {line.type === 'added' && '+ '}
                  {line.type === 'removed' && '- '}
                  {line.type === 'modified' && '~ '}
                  {line.content || ' '}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SplitDiffView({ lines }: { lines: DiffLine[] }) {
  // Build old and new versions
  const oldLines: (string | null)[] = [];
  const newLines: (string | null)[] = [];
  
  lines.forEach((line) => {
    if (line.type === 'removed') {
      oldLines.push(line.content);
      newLines.push(null);
    } else if (line.type === 'added') {
      oldLines.push(null);
      newLines.push(line.content);
    } else if (line.type === 'modified') {
      oldLines.push(line.content);
      newLines.push(line.content);
    } else {
      oldLines.push(line.content);
      newLines.push(line.content);
    }
  });

  const maxLines = Math.max(oldLines.length, newLines.length);

  return (
    <div className="grid grid-cols-2">
      <div className="border-r border-slate-200 overflow-x-auto">
        <div className="p-2 bg-danger-50 border-b border-slate-200 font-medium text-danger-700">Version ancienne (v{lines[0]?.line_number_old || '?'})</div>
        <table className="w-full">
          <tbody>
            {Array.from({ length: maxLines }, (_, i) => (
              <tr key={i} className={cn(
                'border-b border-slate-100',
                oldLines[i] === null && 'bg-slate-50',
                oldLines[i] !== null && newLines[i] !== null && oldLines[i] !== newLines[i] && 'bg-warning-50',
              )}>
                <td className="w-10 text-right p-2 text-slate-400 select-none pr-4">
                  {lines.find(l => l.line_number_old === i + 1)?.line_number_old || ''}
                </td>
                <td className={cn('p-2', oldLines[i] === null && 'text-slate-300 line-through', oldLines[i] !== null && newLines[i] !== null && oldLines[i] !== newLines[i] && 'text-warning-700')}>
                  {oldLines[i] !== null ? `- ${oldLines[i]}` : ' '}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="overflow-x-auto">
        <div className="p-2 bg-success-50 border-b border-slate-200 font-medium text-success-700">Version nouvelle (v{lines[0]?.line_number_new || '?'})</div>
        <table className="w-full">
          <tbody>
            {Array.from({ length: maxLines }, (_, i) => (
              <tr key={i} className={cn(
                'border-b border-slate-100',
                newLines[i] === null && 'bg-slate-50',
                oldLines[i] !== null && newLines[i] !== null && oldLines[i] !== newLines[i] && 'bg-warning-50',
              )}>
                <td className="w-10 text-right p-2 text-slate-400 select-none pr-4">
                  {lines.find(l => l.line_number_new === i + 1)?.line_number_new || ''}
                </td>
                <td className={cn('p-2', newLines[i] === null && 'text-slate-300 line-through', oldLines[i] !== null && newLines[i] !== null && oldLines[i] !== newLines[i] && 'text-warning-700')}>
                  {newLines[i] !== null ? `+ ${newLines[i]}` : ' '}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
