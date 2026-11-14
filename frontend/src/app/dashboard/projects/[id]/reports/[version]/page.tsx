'use client';

import { useParams, useSearchParams } from 'next/navigation';
import { useReportVersion, useReportFindings, useAddContext, useDownloadReport } from '@/hooks/useApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { formatDateTime, getRiskBadgeClass, getConfidenceBadgeClass, getRiskEmoji, getConfidenceEmoji } from '@/lib/utils';
import { AlertTriangle, CheckCircle, FileText, Search, Plus, Download, ArrowLeft, Loader2, Scale, ExternalLink, FileCode, ShieldAlert, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { useState, useMemo } from 'react';
import { toast } from '@/hooks/use-toast';
import type { MatchedArticleDetail, RiskFinding } from '@/lib/api';
import { ArticleDetailDialog } from '@/components/corpus/ArticleDetailDialog';
import { JurisdictionBadge, RuleTypeBadge, SanctionBadge } from '@/components/corpus/corpus-badges';

export default function ReportDetailPage() {
  const params = useParams();
  const versionId = params.version as string;
  const projectId = params.id as string;

  const { data: reportVersion } = useReportVersion(versionId);
  const { data: findings } = useReportFindings(versionId);
  const addContextMutation = useAddContext();
  const downloadMutation = useDownloadReport();
  const [downloadingType, setDownloadingType] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'findings' | 'sources' | 'recommendations'>('findings');
  const [showContextModal, setShowContextModal] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState<MatchedArticleDetail | null>(null);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);

  const openArticleDetail = (art: MatchedArticleDetail) => {
    setSelectedArticle(art);
    setSelectedArticleId(art.id);
  };

  const citedArticles = useMemo(() => {
    const map = new Map<string, MatchedArticleDetail>();
    for (const f of findings || []) {
      for (const art of f.articles_details || []) {
        if (!map.has(art.id)) {
          map.set(art.id, art);
        }
      }
    }
    return Array.from(map.values());
  }, [findings]);

  const downloadReport = (reportType: 'full' | 'report1' | 'report2' = 'full', format: 'pdf' | 'markdown' = 'pdf') => {
    setDownloadingType(`${reportType}-${format}`);
    downloadMutation.mutate(
      { versionId, reportType, format },
      {
        onSettled: () => setDownloadingType(null),
        onError: () => toast({ title: 'Export impossible', description: 'Le fichier du rapport n’a pas pu être téléchargé. Réessayez après la fin de sa génération.', variant: 'destructive' })
      },
    );
  };

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
                    <FindingCard
                      key={finding.id}
                      finding={finding}
                      onOpenArticle={openArticleDetail}
                    />
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
                {citedArticles.length > 0 ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-slate-900">
                        {citedArticles.length} article(s) du Master Corpus cité(s) dans cet audit
                      </p>
                      <Link
                        href="/dashboard/corpus"
                        className="text-xs font-medium text-sovereign-600 hover:underline inline-flex items-center gap-1"
                      >
                        <Scale className="w-3.5 h-3.5" />
                        Explorer toute la bibliothèque
                      </Link>
                    </div>
                    {citedArticles.map((art) => (
                      <div
                        key={art.id}
                        className="p-4 rounded-lg border border-slate-200 bg-slate-50/70 hover:border-sovereign-300 transition-colors space-y-2"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <JurisdictionBadge jurisdiction={art.jurisdiction} />
                            <Badge variant="outline" className="text-[11px] font-mono bg-white">
                              {art.text_code}
                            </Badge>
                            <SanctionBadge hasSanction={art.has_sanction} />
                            <RuleTypeBadge ruleType={art.compliance_rule_type} />
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => openArticleDetail(art)}
                          >
                            Consulter l’article intégral →
                          </Button>
                        </div>
                        <div>
                          <p className="text-sm font-bold text-slate-900">
                            {art.article_number}
                            {art.title ? ` — ${art.title}` : ''}
                          </p>
                          <p className="text-xs text-slate-500">
                            {art.text_title}
                            {art.section_breadcrumb ? ` • ${art.section_breadcrumb}` : ''}
                          </p>
                        </div>
                        <p className="text-xs text-slate-700 line-clamp-3 leading-relaxed">
                          {art.full_text}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : findings && findings.some((f) => f.matched_sources && f.matched_sources.length > 0) ? (
                  <>
                    {findings.map((finding) => (
                      finding.matched_sources && finding.matched_sources.length > 0 && (
                        <SourceCard key={finding.id} finding={finding} />
                      )
                    ))}
                  </>
                ) : (
                  <div className="text-center py-8 text-slate-500">Aucune source ou article cité</div>
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
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>Exports partiels :</span>
          <Button variant="ghost" size="sm" className="h-8 px-2 text-xs text-slate-600 hover:text-slate-900" onClick={() => downloadReport('report1', 'pdf')} disabled={downloadMutation.isPending}>
            {downloadingType === 'report1-pdf' ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Download className="mr-1 h-3 w-3" />}
            Volet Analyse
          </Button>
          <Button variant="ghost" size="sm" className="h-8 px-2 text-xs text-slate-600 hover:text-slate-900" onClick={() => downloadReport('report2', 'pdf')} disabled={downloadMutation.isPending}>
            {downloadingType === 'report2-pdf' ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Download className="mr-1 h-3 w-3" />}
            Volet Articles
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" onClick={() => downloadReport('full', 'markdown')} disabled={downloadMutation.isPending}>
            {downloadingType === 'full-markdown' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
            Exporter en Markdown (Complet)
          </Button>
          <Button className="bg-sovereign-600 hover:bg-sovereign-700 text-white" onClick={() => downloadReport('full', 'pdf')} disabled={downloadMutation.isPending}>
            {downloadingType === 'full-pdf' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
            Télécharger le Rapport Complet (PDF)
          </Button>
          <Button variant="outline" asChild>
            <Link href={`/dashboard/projects/${projectId}/reports/${versionId}/diff?compare=${reportVersion.parent_version_id || ''}`}>
              <Search className="h-4 w-4 mr-2" />
              Voir les différences
            </Link>
          </Button>
        </div>
      </div>

      {/* Add Context Modal */}
      {showContextModal && (
        <AddContextModal
          onClose={() => setShowContextModal(false)}
          onSubmit={handleAddContext}
          vagueZones={extractVagueZones(reportVersion.report1_markdown)}
        />
      )}

      {/* Article Detail Modal */}
      <ArticleDetailDialog
        articleId={selectedArticleId}
        initialArticle={selectedArticle}
        onClose={() => {
          setSelectedArticleId(null);
          setSelectedArticle(null);
        }}
        onSelectArticle={(nextId) => {
          setSelectedArticle(null);
          setSelectedArticleId(nextId);
        }}
      />
    </div>
  );
}

function parseStructuredFindingText(raw: string) {
  const lines = (raw || '').split('\n').map((l) => l.trim()).filter(Boolean);
  const body: string[] = [];
  let paradeLine: string | null = null;
  let paradeVerified = false;
  let legalRiskLine: string | null = null;

  for (const line of lines) {
    if (line.startsWith('Parade d\'annulation vérifiée :') || line.startsWith("Parade d'annulation vérifiée :")) {
      paradeLine = line.replace(/^Parade d['’]annulation vérifiée\s*:\s*/i, '');
      paradeVerified = true;
    } else if (line.startsWith('Parade d\'annulation :') || line.startsWith("Parade d'annulation :")) {
      paradeLine = line.replace(/^Parade d['’]annulation\s*:\s*/i, '');
      paradeVerified = false;
    } else if (line.startsWith('Risque légal encouru :')) {
      legalRiskLine = line.replace(/^Risque légal encouru\s*:\s*/i, '');
    } else if (line.startsWith('Articles applicables :')) {
      // Rendered as interactive article chips below
      continue;
    } else {
      body.push(line);
    }
  }
  return {
    mainText: body.join('\n') || raw,
    paradeLine,
    paradeVerified,
    legalRiskLine,
  };
}

function FindingCard({
  finding,
  onOpenArticle,
}: {
  finding: RiskFinding;
  onOpenArticle: (art: MatchedArticleDetail) => void;
}) {
  const parsed = parseStructuredFindingText(finding.finding_text);
  const hasArticles = (finding.articles_details?.length || 0) > 0;

  return (
    <Card className="border-l-4" style={{ borderLeftColor: getRiskColor(finding.risk_level) }}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <Badge variant={finding.risk_level} className="text-sm">
                {getRiskEmoji(finding.risk_level)} {finding.risk_level.toUpperCase()}
              </Badge>
              <Badge variant={finding.confidence} className="text-sm">
                {getConfidenceEmoji(finding.confidence)} {finding.confidence.toUpperCase()}
              </Badge>
              {parsed.paradeLine && (
                parsed.paradeVerified ? (
                  <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-800 border-emerald-200 gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    Parade prouvée
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-xs bg-amber-50 text-amber-800 border-amber-200 gap-1">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                    Aucune parade prouvée
                  </Badge>
                )
              )}
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

            <p className="font-semibold text-slate-900 mb-1">{finding.clause_ref}</p>
            <p className="text-slate-700 mb-3 whitespace-pre-line">{parsed.mainText}</p>

            {parsed.paradeLine && (
              <div
                className={`mb-3 p-2.5 rounded-lg border text-xs flex items-start gap-2 ${
                  parsed.paradeVerified
                    ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                    : 'bg-amber-50/70 border-amber-200 text-amber-900'
                }`}
              >
                {parsed.paradeVerified ? (
                  <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                ) : (
                  <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                )}
                <div>
                  <span className="font-semibold">
                    {parsed.paradeVerified ? 'Mesure compensatoire détectée : ' : 'Vérification multi-documents : '}
                  </span>
                  <span>{parsed.paradeLine}</span>
                </div>
              </div>
            )}

            {parsed.legalRiskLine && (
              <div className="mb-3 p-2.5 rounded-lg border border-red-200 bg-red-50/70 text-xs text-red-900 flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Risque légal encouru : </span>
                  <span>{parsed.legalRiskLine}</span>
                </div>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
              {hasArticles ? (
                <>
                  <span className="font-semibold text-slate-700">Articles cités :</span>
                  {finding.articles_details!.map((art) => (
                    <button
                      key={art.id}
                      type="button"
                      onClick={() => onOpenArticle(art)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-sovereign-50 hover:bg-sovereign-100 text-sovereign-900 border border-sovereign-200 transition-colors font-medium"
                      title={`${art.text_title}${art.section_breadcrumb ? ` — ${art.section_breadcrumb}` : ''}`}
                    >
                      <Scale className="w-3 h-3 text-sovereign-600 shrink-0" />
                      <span className="font-mono text-[11px]">{art.text_code}</span>
                      <span>• {art.article_number}</span>
                      {art.has_sanction && (
                        <span className="w-2 h-2 rounded-full bg-red-600 shrink-0" title="Article avec sanction" />
                      )}
                    </button>
                  ))}
                </>
              ) : finding.sources_details && finding.sources_details.length > 0 ? (
                <>
                  <span className="font-semibold text-slate-700">Sources juridiques :</span>
                  {finding.sources_details.map((src) => (
                    <span
                      key={src.id}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200"
                      title={`${src.title} (${src.authority})`}
                    >
                      <Scale className="w-3 h-3 text-sovereign-600 shrink-0" />
                      <span className="truncate max-w-[180px]">{src.title}</span>
                      {src.original_filename && (
                        <span className="text-[10px] text-slate-500 font-mono">({src.original_filename})</span>
                      )}
                    </span>
                  ))}
                </>
              ) : finding.matched_sources && finding.matched_sources.length > 0 ? (
                <>
                  <span>Sources : </span>
                  {finding.matched_sources.slice(0, 3).map((sid: string, i: number) => (
                    <Badge key={i} variant="outline" className="text-xs font-mono">{sid.slice(0, 8)}...</Badge>
                  ))}
                  {finding.matched_sources.length > 3 && (
                    <Badge variant="outline" className="text-xs">+{finding.matched_sources.length - 3} autres</Badge>
                  )}
                </>
              ) : null}
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
  const sources = finding.sources_details && finding.sources_details.length > 0
    ? finding.sources_details
    : (finding.matched_sources || []).map((sid: string) => ({ id: sid, title: `Source ${sid.slice(0, 8)}...`, authority: 'Autorité officielle' }));

  return (
    <Card className="border border-slate-200 shadow-2xs">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="font-semibold text-slate-900 text-sm">{finding.clause_ref}</p>
          <Badge variant={finding.risk_level} className="text-xs">
            {finding.risk_level.toUpperCase()}
          </Badge>
        </div>
        <p className="text-xs text-slate-600 mb-3">{finding.finding_text}</p>
        <div className="space-y-2">
          {sources.map((src: any) => (
            <div key={src.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-semibold text-xs text-slate-900 truncate">{src.title}</p>
                <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                  <span>{src.authority}</span>
                  {src.level && <span>• {src.level}</span>}
                  {src.article_ref && <span>• {src.article_ref}</span>}
                </div>
                {src.original_filename && (
                  <div className="mt-1 inline-flex items-center gap-1 text-[11px] font-mono text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                    <FileCode className="w-3 h-3 text-emerald-600" />
                    <span>{src.original_filename}</span>
                  </div>
                )}
              </div>
              {src.download_url && (
                <a
                  href={src.download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 p-1.5 rounded border border-slate-200 text-slate-600 hover:text-sovereign-600 hover:bg-white transition-colors"
                  title="Télécharger / Consulter la source officielle"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
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
