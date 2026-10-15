'use client';

import { useParams, useSearchParams } from 'next/navigation';
import { useReportVersion, useReportFindings, useAddContext } from '@/hooks/useApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { formatDateTime, getRiskBadgeClass, getConfidenceBadgeClass, getRiskEmoji, getConfidenceEmoji } from '@/lib/utils';
import { AlertTriangle, CheckCircle, FileText, Search, Plus, Download, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import { toast } from '@/hooks/use-toast';

export default function ReportDetailPage() {
  const params = useParams();
  const versionId = params.version as string;
  const projectId = params.id as string;

  const { data: reportVersion } = useReportVersion(versionId);
  const { data: findings } = useReportFindings(versionId);
  const addContextMutation = useAddContext();
  const [activeTab, setActiveTab] = useState<'findings' | 'sources' | 'recommendations'>('findings');
  const [showContextModal, setShowContextModal] = useState(false);

  const handleAddContext = async (contextData: Record<string, any>) => {
    try {
      await addContextMutation.mutateAsync({ versionId, contextData });
      setShowContextModal(false);
    } catch (err) {
      toast({ title: 'Ajout impossible', description: 'Le contexte n’a pas pu être ajouté au rapport.', variant: 'destructive' });
    }
  };

  if (!reportVersion) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href={`/dashboard/projects/${projectId}`} className="text-sm text-slate-500 hover:underline">
            ← Projet
          </Link>
          <h1 className="page-title">Rapport v{reportVersion.version}</h1>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={reportVersion.confidence_global}>{reportVersion.confidence_global.toUpperCase()}</Badge>
          <Button variant="outline" onClick={() => setShowContextModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Ajouter contexte
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-sm text-slate-500">Score global</p>
            <p className={cn('text-4xl font-bold mt-1', 
              reportVersion.global_score > 70 ? 'text-danger-600' :
              reportVersion.global_score > 40 ? 'text-warning-600' : 'text-success-600'
            )}>
              {reportVersion.global_score}/100
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-sm text-slate-500">Confiance</p>
            <Badge variant={reportVersion.confidence_global} className="text-lg px-4 py-2">
              {getConfidenceEmoji(reportVersion.confidence_global)} {reportVersion.confidence_global.toUpperCase()}
            </Badge>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-sm text-slate-500">Risques détectés</p>
            <p className="text-4xl font-bold text-slate-900 mt-1">
              {Object.values(reportVersion.severity_counts).reduce((a, b) => a + b, 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-sm text-slate-500">Version</p>
            <p className="text-4xl font-bold text-slate-900 mt-1">v{reportVersion.version}</p>
          </CardContent>
        </Card>
      </div>

      {/* Severity Breakdown */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-wrap gap-2">
            {Object.entries(reportVersion.severity_counts).map(([level, count]) => (
              count > 0 && (
                <Badge key={level} variant={level} className="text-sm">
                  {getRiskEmoji(level)} {level.charAt(0).toUpperCase() + level.slice(1)}: {count}
                </Badge>
              )
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Report Tabs */}
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="findings">
            <FileText className="h-4 w-4 mr-2" />
            Constats
          </TabsTrigger>
          <TabsTrigger value="sources">
            <Search className="h-4 w-4 mr-2" />
            Sources juridiques
          </TabsTrigger>
          <TabsTrigger value="recommendations">
            <AlertTriangle className="h-4 w-4 mr-2" />
            Recommandations
          </TabsTrigger>
        </TabsList>

        <TabsContent value="findings" className="mt-4">
          <Card>
            <CardContent className="p-6">
              {findings && findings.length > 0 ? (
                <div className="space-y-4">
                  {findings.map((finding) => (
                    <FindingCard key={finding.id} finding={finding} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">Aucun constat</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sources" className="mt-4">
          <Card>
            <CardContent className="p-6">
              <div className="space-y-4">
                {findings && findings.length > 0 ? (
                  <>
                    {findings.map((finding) => (
                      finding.matched_sources && finding.matched_sources.length > 0 && (
                        <SourceCard key={finding.id} finding={finding} />
                      )
                    ))}
                  </>
                ) : (
                  <div className="text-center py-8 text-slate-500">Aucune source citée</div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recommendations" className="mt-4">
          <Card>
            <CardContent className="p-6">
              <div className="space-y-4">
                {findings && findings.length > 0 ? (
                  findings
                    .filter(f => ['critique', 'eleve', 'modere'].includes(f.risk_level))
                    .map((finding) => (
                      <RecommendationCard key={finding.id} finding={finding} />
                    ))
                ) : (
                  <div className="text-center py-8 text-slate-500">Aucune recommandation</div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Export Buttons */}
      <div className="flex justify-end gap-3">
        <Button variant="outline" asChild>
          <Link href={`/api/reports/${versionId}/export?format=pdf&type=report1`} target="_blank">
            <Download className="h-4 w-4 mr-2" />
            Exporter Rapport 1 (PDF)
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/api/reports/${versionId}/export?format=pdf&type=report2`} target="_blank">
            <Download className="h-4 w-4 mr-2" />
            Exporter Rapport 2 (PDF)
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/api/reports/${versionId}/export?format=markdown&type=report1`} target="_blank">
            <FileText className="h-4 w-4 mr-2" />
            Exporter Rapport 1 (MD)
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/api/reports/${versionId}/export?format=markdown&type=report2`} target="_blank">
            <FileText className="h-4 w-4 mr-2" />
            Exporter Rapport 2 (MD)
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/dashboard/projects/${projectId}/reports/${versionId}/diff?compare=${reportVersion.parent_version_id || ''}`}>
            <Search className="h-4 w-4 mr-2" />
            Voir les différences
          </Link>
        </Button>
      </div>

      {/* Add Context Modal */}
      {showContextModal && (
        <AddContextModal
          onClose={() => setShowContextModal(false)}
          onSubmit={handleAddContext}
          vagueZones={extractVagueZones(reportVersion.report1_markdown)}
        />
      )}
    </div>
  );
}

function FindingCard({ finding }: { finding: any }) {
  return (
    <Card className="border-l-4" style={{ borderLeftColor: getRiskColor(finding.risk_level) }}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <Badge variant={finding.risk_level} className="text-sm">
                {getRiskEmoji(finding.risk_level)} {finding.risk_level.toUpperCase()}
              </Badge>
              <Badge variant={finding.confidence} className="text-sm">
                {getConfidenceEmoji(finding.confidence)} {finding.confidence.toUpperCase()}
              </Badge>
              {finding.obsolescence_flag && (
                <Badge variant="destructive" className="text-sm">
                  ⚠️ Source potentiellement abrogée
                </Badge>
              )}
              {finding.conflict_flag && (
                <Badge variant="warning" className="text-sm">
                  ⚠️ Conflit de normes
                </Badge>
              )}
            </div>
            <p className="font-medium text-slate-900 mb-1">{finding.clause_ref}</p>
            <p className="text-slate-700 mb-3">{finding.finding_text}</p>
            <div className="flex items-center gap-2 text-sm text-slate-600">
              {finding.matched_sources && finding.matched_sources.length > 0 && (
                <>
                  <span>Sources: </span>
                  {finding.matched_sources.slice(0, 3).map((sid: string, i: number) => (
                    <Badge key={i} variant="outline" className="text-xs">{sid.slice(0, 8)}...</Badge>
                  ))}
                  {finding.matched_sources.length > 3 && (
                    <Badge variant="outline" className="text-xs">+{finding.matched_sources.length - 3} autres</Badge>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
        <div className="mt-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
          <p className="font-medium text-slate-900 mb-1">Recommandation</p>
          <p className="text-slate-700">{finding.recommendation}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function SourceCard({ finding }: { finding: any }) {
  return (
    <Card>
      <CardContent className="p-6">
        <p className="font-medium text-slate-900 mb-3">{finding.clause_ref} — {finding.risk_level.toUpperCase()}</p>
        <div className="space-y-2">
          {finding.matched_sources?.map((sid: string) => (
            <div key={sid} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <p className="font-mono text-sm">{sid}</p>
              <p className="text-xs text-slate-500">Source correspondante pour ce constat</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function RecommendationCard({ finding }: { finding: any }) {
  return (
    <Card className="border-l-4" style={{ borderLeftColor: getRiskColor(finding.risk_level) }}>
      <CardContent className="p-6">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant={finding.risk_level}>{finding.risk_level.toUpperCase()}</Badge>
          <span className="font-medium">{finding.clause_ref}</span>
        </div>
        <p className="text-slate-700">{finding.recommendation}</p>
      </CardContent>
    </Card>
  );
}

function getRiskColor(level: string): string {
  switch (level) {
    case 'critique': return '#C41E3A';
    case 'eleve': return '#E67E00';
    case 'modere': return '#E6A800';
    case 'a_surveiller': return '#0052A5';
    case 'conforme': return '#007B3F';
    default: return '#64748B';
  }
}

function extractVagueZones(markdown: string): string[] {
  const zones: string[] = [];
  const lines = markdown.split('\n');
  let inVagueZone = false;
  for (const line of lines) {
    if (line.includes('Zones floues') || line.includes('zones floues')) {
      inVagueZone = true;
      continue;
    }
    if (inVagueZone && line.startsWith('#')) {
      inVagueZone = false;
    }
    if (inVagueZone && line.trim().startsWith('-')) {
      zones.push(line.trim().slice(1).trim());
    }
  }
  return zones;
}

function AddContextModal({ onClose, onSubmit, vagueZones }: { onClose: () => void; onSubmit: (data: Record<string, any>) => void; vagueZones: string[] }) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [selectedZone, setSelectedZone] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ ...formData, vague_zone: selectedZone });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Ajouter un contexte complémentaire</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <p className="text-sm text-slate-600 mb-4">
              L'analyse a détecté des zones floues. Précisez les informations manquantes pour améliorer la précision du rapport.
            </p>
          </div>

          {vagueZones.length > 0 && (
            <div>
              <label className="label">Zone floue concernée *</label>
              <select
                value={selectedZone}
                onChange={(e) => setSelectedZone(e.target.value)}
                className="input"
                required
              >
                <option value="">Sélectionnez une zone floue</option>
                {vagueZones.map((zone, i) => (
                  <option key={i} value={zone}>{zone}</option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="label">Localisation d'hébergement</label>
            <input
              type="text"
              placeholder="ex: Cotonou, Bénin (Datacenter XYZ)"
              value={formData.hosting_location || ''}
              onChange={(e) => setFormData({ ...formData, hosting_location: e.target.value })}
              className="input"
            />
          </div>

          <div>
            <label className="label">Sous-traitant principal</label>
            <input
              type="text"
              placeholder="ex: AWS, OVHcloud, Datacenter local"
              value={formData.subcontractor || ''}
              onChange={(e) => setFormData({ ...formData, subcontractor: e.target.value })}
              className="input"
            />
          </div>

          <div>
            <label className="label">Détails sur les transferts de données</label>
            <textarea
              placeholder="Décrivez les flux de données vers l'extérieur..."
              value={formData.transfer_details || ''}
              onChange={(e) => setFormData({ ...formData, transfer_details: e.target.value })}
              className="input min-h-[80px]"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
            <Button type="button" variant="secondary" onClick={onClose}>
              Annuler
            </Button>
            <Button type="submit">
              Envoyer et mettre à jour le rapport
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

import { cn } from '@/lib/utils';
