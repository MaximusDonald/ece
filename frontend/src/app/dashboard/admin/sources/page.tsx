'use client';

import * as React from 'react';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  useAdminSources,
  useAdminAlerts,
  useAdminSourceCollections,
  useCollectSource,
  useCreateSource,
  useUpdateSource,
  useDeleteSource,
  useReviewAlert,
} from '@/hooks/useApi';
import {
  BellRing,
  CheckCircle2,
  Edit,
  ExternalLink,
  Globe,
  History,
  Loader2,
  Plus,
  RefreshCw,
  Scale,
  Search,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  XCircle,
} from 'lucide-react';
import { formatDateTime } from '@/lib/utils';
import { toast } from '@/hooks/use-toast';
import type { LegalSource, RegulatoryAlertItem } from '@/lib/api';

const COUNTRY_OPTIONS = [
  { value: 'ALL', label: 'Toutes les juridictions' },
  { value: 'BJ', label: 'Bénin (BJ)' },
  { value: 'SN', label: 'Sénégal (SN)' },
  { value: 'CI', label: "Côte d'Ivoire (CI)" },
  { value: 'TG', label: 'Togo (TG)' },
  { value: 'BF', label: 'Burkina Faso (BF)' },
];

export default function RegulatorySentinelPage() {
  const { data: sources, isLoading: loadingSources, refetch: refetchSources } = useAdminSources();
  const [alertStatusFilter, setAlertStatusFilter] = React.useState<'pending_review' | 'all'>('pending_review');
  const { data: alerts, isLoading: loadingAlerts, refetch: refetchAlerts } = useAdminAlerts({
    status: alertStatusFilter === 'all' ? undefined : alertStatusFilter,
  });

  const createSource = useCreateSource();
  const updateSource = useUpdateSource();
  const deleteSource = useDeleteSource();
  const collectSource = useCollectSource();
  const reviewAlert = useReviewAlert();

  const [activeTab, setActiveTab] = React.useState<'alerts' | 'feeds'>('alerts');
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [editingSource, setEditingSource] = React.useState<LegalSource | null>(null);
  const [historySourceId, setHistorySourceId] = React.useState<string | undefined>();
  const [checkingSourceId, setCheckingSourceId] = React.useState<string | null>(null);
  const [searchFilter, setSearchFilter] = React.useState('');
  const [countryFilter, setCountryFilter] = React.useState('ALL');

  const { data: collectionRuns, isLoading: isHistoryLoading } = useAdminSourceCollections(historySourceId);

  const [formData, setFormData] = React.useState({
    title: '',
    authority: '',
    country_code: 'BJ',
    level: 'loi',
    url_official: '',
    collection_enabled: true,
  });

  const pendingCount = React.useMemo(
    () => (alerts || []).filter((a) => a.status === 'pending_review').length,
    [alerts]
  );

  const handleOpenCreate = () => {
    setFormData({
      title: '',
      authority: '',
      country_code: 'BJ',
      level: 'loi',
      url_official: '',
      collection_enabled: true,
    });
    setIsCreateOpen(true);
  };

  const handleOpenEdit = (source: LegalSource) => {
    setEditingSource(source);
    setFormData({
      title: source.title,
      authority: source.authority,
      country_code: source.country_code || 'ALL',
      level: source.level || 'loi',
      url_official: source.url_official,
      collection_enabled: Boolean(source.collection_enabled),
    });
  };

  const handleSaveForm = async (e: React.FormEvent) => {
    e.preventDefault();
    const countryVal = formData.country_code === 'ALL' ? null : formData.country_code;
    try {
      if (editingSource) {
        await updateSource.mutateAsync({
          id: editingSource.id,
          data: {
            title: formData.title,
            authority: formData.authority,
            country_code: countryVal,
            level: formData.level,
            url_official: formData.url_official,
            crawl_depth: 1,
            collection_enabled: formData.collection_enabled,
          },
        });
        toast({ title: 'Flux de veille mis à jour' });
        setEditingSource(null);
      } else {
        await createSource.mutateAsync({
          title: formData.title,
          authority: formData.authority,
          country_code: countryVal,
          level: formData.level,
          url_official: formData.url_official,
          crawl_depth: 1,
          collection_enabled: formData.collection_enabled,
          is_portal: true,
          article_ref: `VEILLE-${countryVal || 'REG'}`,
          content_text: `Flux de veille Sentinelle : ${formData.title} (${formData.authority})`,
        });
        toast({ title: 'Flux de veille ajouté' });
        setIsCreateOpen(false);
      }
      refetchSources();
    } catch (error: any) {
      toast({
        title: 'Erreur',
        description: error?.response?.data?.detail || 'Impossible d’enregistrer le flux de veille.',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteSource = async (source: LegalSource) => {
    if (!confirm(`Retirer la cible de veille "${source.title}" ?`)) return;
    try {
      await deleteSource.mutateAsync(source.id);
      toast({ title: 'Cible de veille supprimée' });
      refetchSources();
      refetchAlerts();
    } catch (err: any) {
      toast({
        title: 'Erreur',
        description: err?.response?.data?.detail || 'Suppression impossible.',
        variant: 'destructive',
      });
    }
  };

  const handleCheckSentinelNow = async (source: LegalSource) => {
    setCheckingSourceId(source.id);
    try {
      const run = await collectSource.mutateAsync({ id: source.id, depth: 1 });
      if (run?.status === 'unchanged') {
        toast({
          title: 'Aucun changement détecté',
          description: `${source.title} : empreinte ETag / SHA-256 identique.`,
        });
      } else {
        toast({
          title: 'Vérification Sentinelle terminée',
          description: `${source.title} : changement détecté, consultez l’onglet Alertes pour validation.`,
        });
      }
      refetchSources();
      refetchAlerts();
    } catch (error: any) {
      toast({
        title: 'Erreur Sentinelle',
        description: error?.response?.data?.detail || 'La vérification a échoué.',
        variant: 'destructive',
      });
    } finally {
      setCheckingSourceId(null);
    }
  };

  const handleReviewAlert = async (alert: RegulatoryAlertItem, action: 'approve' | 'dismiss') => {
    try {
      await reviewAlert.mutateAsync({ id: alert.id, action });
      toast({
        title: action === 'approve' ? 'Alerte validée' : 'Alerte ignorée',
        description:
          action === 'approve'
            ? 'Le document détecté est validé pour ingestion contrôlée dans le Master Corpus.'
            : 'L’alerte a été classée sans suite.',
      });
      refetchAlerts();
    } catch (error: any) {
      toast({
        title: 'Action impossible',
        description: error?.response?.data?.detail || 'Erreur lors de la validation.',
        variant: 'destructive',
      });
    }
  };

  const filteredSources = React.useMemo(() => {
    return (sources || []).filter((s) => {
      const matchesCountry = countryFilter === 'ALL' || (s.country_code || '') === countryFilter;
      const q = searchFilter.trim().toLowerCase();
      const matchesSearch =
        !q ||
        s.title.toLowerCase().includes(q) ||
        s.authority.toLowerCase().includes(q) ||
        s.url_official.toLowerCase().includes(q);
      return matchesCountry && matchesSearch;
    });
  }, [sources, countryFilter, searchFilter]);

  const getRunBadge = (status?: string | null) => {
    switch (status) {
      case 'unchanged':
        return <Badge variant="outline" className="text-[11px] bg-slate-50 text-slate-700">Inchangé</Badge>;
      case 'succeeded':
        return <Badge variant="outline" className="text-[11px] bg-amber-50 text-amber-800 border-amber-200">Changement détecté</Badge>;
      case 'running':
      case 'queued':
        return <Badge variant="outline" className="text-[11px] bg-blue-50 text-blue-700">Vérification…</Badge>;
      case 'failed':
        return <Badge variant="outline" className="text-[11px] bg-rose-50 text-rose-700">Échec</Badge>;
      default:
        return <span className="text-xs text-slate-400">Jamais vérifié</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
            <BellRing className="w-6 h-6 text-sovereign-600" />
            <span>Sentinelle Réglementaire & Veille Active</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Surveillance ciblée (ETag / SHA-256) des journaux officiels, arrêtés ministériels et délibérations APDP. Aucune ingestion automatique sans validation administrateur.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/dashboard/admin/corpus">
            <Button variant="outline" className="gap-2">
              <Scale className="w-4 h-4 text-sovereign-600" />
              <span>Bibliothèque des Codes</span>
            </Button>
          </Link>
          <Button onClick={handleOpenCreate} className="gap-2 bg-sovereign-600 hover:bg-sovereign-700 text-white">
            <Plus className="w-4 h-4" />
            <span>Ajouter un flux de veille</span>
          </Button>
        </div>
      </div>

      {/* Safeguard Info Banner */}
      <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
        <div className="text-xs text-emerald-950 space-y-0.5">
          <p className="font-semibold">Mode Aspiration Aveugle désactivé</p>
          <p className="text-emerald-800">
            Le crawler ne parcourt plus récursivement les sites institutionnels. La Sentinelle calcule uniquement les empreintes HTTP (`ETag`, `Last-Modified`, `SHA-256`) des pages ciblées et génère une alerte en attente lorsqu’un nouvel acte normatif est publié.
          </p>
        </div>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-white border-slate-200">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Alertes en attente</p>
              <p className="text-2xl font-bold text-amber-700 mt-1">{pendingCount}</p>
            </div>
            <ShieldAlert className="w-6 h-6 text-amber-600 opacity-80" />
          </CardContent>
        </Card>
        <Card className="bg-white border-slate-200">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Flux surveillés</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{sources?.length || 0}</p>
            </div>
            <Globe className="w-6 h-6 text-sovereign-600 opacity-80" />
          </CardContent>
        </Card>
        <Card className="bg-white border-slate-200">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Cadence automatique</p>
              <p className="text-sm font-bold text-slate-900 mt-1">Hebdomadaire (Lundi 02:00 UTC)</p>
              <p className="text-[11px] text-slate-400">Contrôle manuel disponible à tout moment</p>
            </div>
            <RefreshCw className="w-5 h-5 text-emerald-600 opacity-80" />
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'alerts' | 'feeds')} className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="alerts" className="gap-2">
            <BellRing className="w-4 h-4" />
            <span>Alertes réglementaires ({alerts?.length || 0})</span>
          </TabsTrigger>
          <TabsTrigger value="feeds" className="gap-2">
            <Globe className="w-4 h-4" />
            <span>Flux surveillés ({sources?.length || 0})</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Regulatory Alerts */}
        <TabsContent value="alerts" className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50">
              <button
                type="button"
                onClick={() => setAlertStatusFilter('pending_review')}
                className={`px-3 py-1 rounded-md text-xs font-medium ${
                  alertStatusFilter === 'pending_review' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600'
                }`}
              >
                À valider uniquement
              </button>
              <button
                type="button"
                onClick={() => setAlertStatusFilter('all')}
                className={`px-3 py-1 rounded-md text-xs font-medium ${
                  alertStatusFilter === 'all' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600'
                }`}
              >
                Tout l’historique
              </button>
            </div>
          </div>

          {loadingAlerts ? (
            <Card>
              <CardContent className="py-12 flex justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-sovereign-600" />
              </CardContent>
            </Card>
          ) : alerts && alerts.length > 0 ? (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <Card key={alert.id} className="border-slate-200 bg-white">
                  <CardContent className="p-5 space-y-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline" className="font-mono text-xs bg-sovereign-50 text-sovereign-700 border-sovereign-200">
                            {alert.jurisdiction}
                          </Badge>
                          <Badge
                            variant="outline"
                            className={
                              alert.status === 'pending_review'
                                ? 'bg-amber-50 text-amber-800 border-amber-200 text-xs'
                                : alert.status === 'approved'
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-200 text-xs'
                                : 'bg-slate-100 text-slate-600 text-xs'
                            }
                          >
                            {alert.status === 'pending_review'
                              ? 'En attente de validation'
                              : alert.status === 'approved'
                              ? 'Validée pour ingestion'
                              : 'Ignorée'}
                          </Badge>
                          <span className="text-xs text-slate-500">{alert.authority}</span>
                        </div>
                        <h3 className="text-base font-semibold text-slate-900">{alert.title}</h3>
                        <a
                          href={alert.detected_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-mono text-sovereign-600 hover:underline break-all"
                        >
                          <span>{alert.detected_url}</span>
                          <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      </div>

                      <div className="text-right text-[11px] text-slate-500 shrink-0">
                        <div>Détectée : {formatDateTime(alert.detected_at)}</div>
                        <div className="font-mono mt-0.5">
                          SHA-256 : {alert.new_hash.slice(0, 12)}…
                        </div>
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                      {alert.change_summary}
                    </div>

                    {alert.status === 'pending_review' && (
                      <div className="flex flex-wrap justify-end gap-2 pt-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleReviewAlert(alert, 'dismiss')}
                          disabled={reviewAlert.isPending}
                          className="text-slate-600"
                        >
                          <XCircle className="w-4 h-4 mr-1.5" />
                          Ignorer
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleReviewAlert(alert, 'approve')}
                          disabled={reviewAlert.isPending}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        >
                          <CheckCircle2 className="w-4 h-4 mr-1.5" />
                          Valider avant ingestion
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="border-slate-200">
              <CardContent className="py-12 text-center space-y-2">
                <ShieldCheck className="w-10 h-10 text-emerald-500 mx-auto" />
                <p className="text-sm font-semibold text-slate-900">
                  Aucune alerte en attente
                </p>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Déclenchez une vérification manuelle dans l’onglet « Flux surveillés » ou attendez le prochain cycle de veille hebdomadaire.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Tab 2: Watch Feeds */}
        <TabsContent value="feeds" className="mt-4 space-y-4">
          <Card className="bg-white border-slate-200">
            <CardContent className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Filtrer par autorité, titre ou URL…"
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="pl-9 text-sm"
                />
              </div>
              <Select value={countryFilter} onValueChange={setCountryFilter}>
                <SelectTrigger className="text-sm">
                  <SelectValue placeholder="Juridiction" />
                </SelectTrigger>
                <SelectContent>
                  {COUNTRY_OPTIONS.map((c) => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <Card className="bg-white border-slate-200">
            <CardContent className="p-0">
              {loadingSources ? (
                <div className="py-12 flex justify-center">
                  <Loader2 className="w-6 h-6 animate-spin text-sovereign-600" />
                </div>
              ) : filteredSources.length > 0 ? (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50/70">
                        <TableHead>Source officielle surveillée</TableHead>
                        <TableHead>Juridiction</TableHead>
                        <TableHead>URL ciblée</TableHead>
                        <TableHead>Dernier contrôle</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredSources.map((source) => (
                        <TableRow key={source.id}>
                          <TableCell>
                            <p className="font-semibold text-sm text-slate-900">{source.title}</p>
                            <p className="text-xs text-slate-500">{source.authority}</p>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="font-mono text-xs">
                              {source.country_code || 'REGIONAL'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <a
                              href={source.url_official}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs font-mono text-sovereign-600 hover:underline max-w-[260px] truncate"
                            >
                              <span className="truncate">{source.url_official}</span>
                              <ExternalLink className="w-3 h-3 shrink-0" />
                            </a>
                          </TableCell>
                          <TableCell className="text-xs space-y-1">
                            <div className="text-slate-700">
                              {source.last_collection_at ? formatDateTime(source.last_collection_at) : 'Jamais'}
                            </div>
                            <div>{getRunBadge(source.last_collection_status)}</div>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="inline-flex items-center gap-1">
                              <Button
                                size="sm"
                                className="h-8 text-xs bg-sovereign-600 hover:bg-sovereign-700 text-white gap-1.5"
                                onClick={() => handleCheckSentinelNow(source)}
                                disabled={checkingSourceId === source.id}
                              >
                                {checkingSourceId === source.id ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                  <RefreshCw className="w-3.5 h-3.5" />
                                )}
                                <span>Vérifier maintenant</span>
                              </Button>
                              <Button
                                variant="outline"
                                size="icon"
                                className="h-8 w-8"
                                title="Historique des contrôles"
                                onClick={() => setHistorySourceId(source.id)}
                              >
                                <History className="w-3.5 h-3.5" />
                              </Button>
                              <Button
                                variant="outline"
                                size="icon"
                                className="h-8 w-8"
                                title="Modifier"
                                onClick={() => handleOpenEdit(source)}
                              >
                                <Edit className="w-3.5 h-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-rose-600 hover:bg-rose-50"
                                title="Supprimer"
                                onClick={() => handleDeleteSource(source)}
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="py-12 text-center text-sm text-slate-500">
                  Aucun flux de veille configuré.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Modal: Create / Edit Watch Target */}
      <Dialog
        open={isCreateOpen || Boolean(editingSource)}
        onOpenChange={(open) => {
          if (!open) {
            setIsCreateOpen(false);
            setEditingSource(null);
          }
        }}
      >
        <DialogContent className="max-w-lg">
          <form onSubmit={handleSaveForm} className="space-y-4">
            <DialogHeader>
              <DialogTitle>{editingSource ? 'Modifier le flux surveillé' : 'Ajouter un flux officiel de veille'}</DialogTitle>
              <DialogDescription>
                La Sentinelle inspecte uniquement cette URL ciblée par empreinte ETag / SHA-256 (pas d’aspiration récursive).
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="sentinel-title">Nom du flux / rubrique</Label>
                <Input
                  id="sentinel-title"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="ex: APDP Bénin — Délibérations"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="sentinel-auth">Autorité</Label>
                  <Input
                    id="sentinel-auth"
                    value={formData.authority}
                    onChange={(e) => setFormData({ ...formData, authority: e.target.value })}
                    placeholder="APDP Bénin"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="sentinel-country">Juridiction</Label>
                  <Select
                    value={formData.country_code}
                    onValueChange={(val) => setFormData({ ...formData, country_code: val })}
                  >
                    <SelectTrigger id="sentinel-country">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {COUNTRY_OPTIONS.map((c) => (
                        <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sentinel-url">URL HTTPS ciblée</Label>
                <Input
                  id="sentinel-url"
                  type="url"
                  value={formData.url_official}
                  onChange={(e) => setFormData({ ...formData, url_official: e.target.value })}
                  placeholder="https://service.apdp.bj/documentation"
                  required
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setIsCreateOpen(false); setEditingSource(null); }}>
                Annuler
              </Button>
              <Button type="submit" className="bg-sovereign-600 hover:bg-sovereign-700 text-white">
                {editingSource ? 'Mettre à jour' : 'Enregistrer'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal: History */}
      <Dialog open={Boolean(historySourceId)} onOpenChange={(open) => !open && setHistorySourceId(undefined)}>
        <DialogContent className="max-w-xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Historique des contrôles Sentinelle</DialogTitle>
            <DialogDescription>Empreintes HTTP/SHA-256 et alertes détectées par cycle.</DialogDescription>
          </DialogHeader>
          {isHistoryLoading ? (
            <div className="py-8 flex justify-center"><Loader2 className="w-5 h-5 animate-spin" /></div>
          ) : collectionRuns && collectionRuns.length > 0 ? (
            <div className="space-y-2.5">
              {collectionRuns.map((run) => (
                <div key={run.id} className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    {getRunBadge(run.status)}
                    <span className="font-mono text-slate-500">
                      {run.started_at ? formatDateTime(run.started_at) : formatDateTime(run.requested_at)}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-3 text-slate-600">
                    <span>HTTP : {run.http_status_code ?? '—'}</span>
                    <span>Liens normatifs : {run.discovered_urls_count ?? 0}</span>
                    <span>Alertes créées : {run.ai_processed_count ?? 0}</span>
                  </div>
                  {run.error_message && (
                    <p className="text-rose-700 bg-rose-50 border border-rose-200 rounded p-2">{run.error_message}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-6 text-sm text-slate-500">Aucun contrôle effectué pour cette cible.</p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
