'use client';

import * as React from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
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
  useAdminSourceCollections,
  useCollectSource,
  useCreateSource,
  useUpdateSource,
  useDeleteSource,
} from '@/hooks/useApi';
import {
  Plus,
  Search,
  CheckCircle,
  AlertTriangle,
  Clock,
  ExternalLink,
  History,
  Loader2,
  Play,
  Globe,
  FileText,
  Trash2,
  Edit,
  Sparkles,
  Layers,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import { formatDateTime } from '@/lib/utils';
import { toast } from '@/hooks/use-toast';
import type { LegalSource } from '@/lib/api';

const STATUS_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'verified', label: 'Vérifiée' },
  { value: 'to_verify', label: 'À vérifier' },
  { value: 'replaced', label: 'Remplacée' },
  { value: 'archived', label: 'Archivée' },
  { value: 'disputed', label: 'Contestée' },
  { value: 'unofficial', label: 'Non officielle' },
];

const COUNTRY_OPTIONS = [
  { value: '', label: 'Toutes les juridictions' },
  { value: 'BJ', label: 'Bénin (BJ)' },
  { value: 'SN', label: 'Sénégal (SN)' },
  { value: 'CI', label: "Côte d'Ivoire (CI)" },
  { value: 'TG', label: 'Togo (TG)' },
  { value: 'BF', label: 'Burkina Faso (BF)' },
  { value: 'NE', label: 'Niger (NE)' },
  { value: 'ML', label: 'Mali (ML)' },
  { value: 'GN', label: 'Guinée (GN)' },
  { value: 'GW', label: 'Guinée-Bissau (GW)' },
  { value: 'CV', label: 'Cap-Vert (CV)' },
  { value: 'GH', label: 'Ghana (GH)' },
  { value: 'NG', label: 'Nigéria (NG)' },
  { value: 'LR', label: 'Libéria (LR)' },
  { value: 'SL', label: 'Sierra Leone (SL)' },
  { value: 'GM', label: 'Gambie (GM)' },
];

export default function AdminSourcesPage() {
  const { data: sources, isLoading, refetch } = useAdminSources();
  const createSource = useCreateSource();
  const updateSource = useUpdateSource();
  const deleteSource = useDeleteSource();
  const collectSource = useCollectSource();

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [editingSource, setEditingSource] = React.useState<LegalSource | null>(null);
  const [historySourceId, setHistorySourceId] = React.useState<string | undefined>();
  const [collectingSource, setCollectingSource] = React.useState<LegalSource | null>(null);
  const [crawlDepth, setCrawlDepth] = React.useState<number>(2);

  // Filters state
  const [filters, setFilters] = React.useState({
    status: '',
    country_code: '',
    search: '',
  });

  // History query
  const { data: collectionRuns, isLoading: isHistoryLoading } = useAdminSourceCollections(historySourceId);

  // Form state
  const [formData, setFormData] = React.useState({
    title: '',
    authority: '',
    country_code: 'BJ',
    level: 'loi',
    url_official: '',
    crawl_depth: 2,
    collection_enabled: true,
  });

  const handleOpenCreate = () => {
    setFormData({
      title: '',
      authority: '',
      country_code: 'BJ',
      level: 'loi',
      url_official: '',
      crawl_depth: 2,
      collection_enabled: true,
    });
    setIsCreateOpen(true);
  };

  const handleOpenEdit = (source: LegalSource) => {
    setEditingSource(source);
    setFormData({
      title: source.title,
      authority: source.authority,
      country_code: source.country_code || '',
      level: source.level || 'loi',
      url_official: source.url_official,
      crawl_depth: source.crawl_depth || 2,
      collection_enabled: Boolean(source.collection_enabled),
    });
  };

  const handleSaveForm = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingSource) {
        await updateSource.mutateAsync({
          id: editingSource.id,
          data: {
            title: formData.title,
            authority: formData.authority,
            country_code: formData.country_code || null,
            level: formData.level,
            url_official: formData.url_official,
            crawl_depth: formData.crawl_depth,
            collection_enabled: formData.collection_enabled,
          },
        });
        toast({ title: 'Portail mis à jour', description: 'Les paramètres du portail ont été modifiés.' });
        setEditingSource(null);
      } else {
        await createSource.mutateAsync({
          title: formData.title,
          authority: formData.authority,
          country_code: formData.country_code || null,
          level: formData.level,
          url_official: formData.url_official,
          crawl_depth: formData.crawl_depth,
          collection_enabled: formData.collection_enabled,
          is_portal: true,
          article_ref: 'Portail officiel',
          content_text: `Portail institutionnel officiel : ${formData.title} (${formData.authority})`,
        });
        toast({ title: 'Nouveau portail configuré', description: 'Le portail a été enregistré avec succès.' });
        setIsCreateOpen(false);
      }
      refetch();
    } catch (error: any) {
      toast({
        title: 'Erreur',
        description: error?.response?.data?.detail || 'Impossible d’enregistrer le portail.',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async (source: LegalSource) => {
    if (!confirm(`Supprimer le portail "${source.title}" et tous ses textes indexés ? Cette action est irréversible.`)) {
      return;
    }
    try {
      await deleteSource.mutateAsync(source.id);
      toast({ title: 'Portail supprimé', description: 'Le portail et ses documents associés ont été retirés.' });
      refetch();
    } catch (err: any) {
      toast({
        title: 'Erreur de suppression',
        description: err?.response?.data?.detail || 'Impossible de supprimer cette source.',
        variant: 'destructive',
      });
    }
  };

  const handleTriggerCollect = async () => {
    if (!collectingSource) return;
    try {
      await collectSource.mutateAsync({
        id: collectingSource.id,
        depth: crawlDepth,
      });
      toast({
        title: 'Collecte IA initiée',
        description: `Le robot explore "${collectingSource.title}" à profondeur ${crawlDepth}. Les PDF trouvés seront analysés par l'IA.`,
      });
      setCollectingSource(null);
      refetch();
    } catch (error: any) {
      toast({
        title: 'Échec de lancement',
        description: error?.response?.data?.detail || 'Une collecte est déjà en cours ou une erreur est survenue.',
        variant: 'destructive',
      });
    }
  };

  const filteredSources = React.useMemo(() => {
    return (
      sources?.filter((s) => {
        const matchesStatus = !filters.status || s.status === filters.status;
        const matchesCountry = !filters.country_code || s.country_code === filters.country_code;
        const matchesSearch =
          !filters.search ||
          s.title.toLowerCase().includes(filters.search.toLowerCase()) ||
          s.authority.toLowerCase().includes(filters.search.toLowerCase()) ||
          s.url_official.toLowerCase().includes(filters.search.toLowerCase());
        return matchesStatus && matchesCountry && matchesSearch;
      }) || []
    );
  }, [sources, filters]);

  const totalDocumentsDiscovered = React.useMemo(() => {
    return sources?.reduce((acc, s) => acc + (s.child_documents_count || 0), 0) || 0;
  }, [sources]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return (
          <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-xs">
            <CheckCircle className="h-3 w-3 mr-1 text-emerald-600" />
            Vérifiée
          </Badge>
        );
      case 'to_verify':
        return (
          <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">
            <Clock className="h-3 w-3 mr-1 text-amber-600" />
            À vérifier
          </Badge>
        );
      case 'disputed':
        return (
          <Badge variant="outline" className="bg-rose-50 text-rose-700 border-rose-200 text-xs">
            <AlertTriangle className="h-3 w-3 mr-1 text-rose-600" />
            Contestée
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary" className="text-xs">
            {status}
          </Badge>
        );
    }
  };

  const getRunBadge = (status?: string | null) => {
    switch (status) {
      case 'succeeded':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-100 text-emerald-800">Succès</span>;
      case 'running':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-100 text-blue-800">
            <Loader2 className="w-2.5 h-2.5 mr-1 animate-spin" />
            En cours
          </span>
        );
      case 'queued':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-purple-100 text-purple-800">En attente</span>;
      case 'failed':
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-rose-100 text-rose-800">Échec</span>;
      default:
        return <span className="text-xs text-slate-400">Aucune</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Navigation Tabs Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Portails institutionnels & Collecte IA</h1>
          <p className="text-sm text-slate-500 mt-1">
            Gérez les URLs d'autorités nationales et orchestrez le crawler intelligent avec extraction de PDF et de règles juridiques.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/dashboard/admin/sources/documents">
            <Button variant="outline" className="gap-2 border-slate-200 hover:bg-slate-50">
              <FileText className="w-4 h-4 text-sovereign-600" />
              <span>Voir les textes extraits</span>
              <Badge variant="secondary" className="ml-1 text-xs px-1.5 py-0">
                {totalDocumentsDiscovered}
              </Badge>
              <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
            </Button>
          </Link>
          <Button onClick={handleOpenCreate} className="gap-2 bg-sovereign-600 hover:bg-sovereign-700 text-white">
            <Plus className="w-4 h-4" />
            <span>Nouveau portail</span>
          </Button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-white border-slate-200 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Portails configurés</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{sources?.length || 0}</h3>
              <p className="text-xs text-slate-400 mt-0.5">Autorités de régulation & ministères</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600">
              <Globe className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border-slate-200 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Documents & Lois découverts</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{totalDocumentsDiscovered}</h3>
              <p className="text-xs text-emerald-600 font-medium mt-0.5 flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Extraits & analysés par IA
              </p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
              <FileText className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border-slate-200 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Moteur de collecte</p>
              <h3 className="text-base font-bold text-slate-900 mt-1 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                Crawler & IA actifs
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Exploration multi-niveaux & MinIO S3</p>
            </div>
            <div className="w-12 h-12 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600">
              <Layers className="w-6 h-6" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters Card */}
      <Card className="bg-white border-slate-200 shadow-xs">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Rechercher par autorité, titre, URL..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="pl-9 text-sm"
              />
            </div>
            <Select
              value={filters.country_code}
              onValueChange={(val) => setFilters({ ...filters, country_code: val })}
            >
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Toutes les juridictions" />
              </SelectTrigger>
              <SelectContent>
                {COUNTRY_OPTIONS.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={filters.status}
              onValueChange={(val) => setFilters({ ...filters, status: val })}
            >
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Tous les statuts" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Portals Table */}
      <Card className="bg-white border-slate-200 shadow-xs">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="w-8 h-8 text-sovereign-600 animate-spin" />
              <p className="text-sm text-slate-500">Chargement des portails officiels...</p>
            </div>
          ) : filteredSources.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/70 border-b border-slate-200">
                    <TableHead className="font-semibold text-slate-700">Portail & Autorité</TableHead>
                    <TableHead className="font-semibold text-slate-700">Juridiction</TableHead>
                    <TableHead className="font-semibold text-slate-700">URL Officielle</TableHead>
                    <TableHead className="font-semibold text-slate-700 text-center">Profondeur</TableHead>
                    <TableHead className="font-semibold text-slate-700 text-center">Documents extraits</TableHead>
                    <TableHead className="font-semibold text-slate-700">Dernière collecte</TableHead>
                    <TableHead className="font-semibold text-slate-700">Statut</TableHead>
                    <TableHead className="text-right font-semibold text-slate-700">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredSources.map((source) => (
                    <TableRow key={source.id} className="hover:bg-slate-50/60 border-b border-slate-100">
                      <TableCell className="py-3.5">
                        <div className="flex items-start gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-sovereign-50 flex items-center justify-center text-sovereign-700 shrink-0 mt-0.5 border border-sovereign-100">
                            <Globe className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <span className="font-semibold text-slate-900 text-sm block truncate max-w-[240px]">
                              {source.title}
                            </span>
                            <span className="text-xs text-slate-500 block truncate max-w-[240px]">
                              {source.authority}
                            </span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="py-3.5">
                        {source.country_code ? (
                          <Badge variant="outline" className="font-mono text-xs font-semibold bg-slate-50 text-slate-700 border-slate-200">
                            {source.country_code.toUpperCase()}
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="text-xs">
                            Supranational
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="py-3.5">
                        <a
                          href={source.url_official}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs text-sovereign-600 hover:text-sovereign-800 hover:underline max-w-[220px] truncate font-mono"
                        >
                          <span className="truncate">{source.url_official}</span>
                          <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      </TableCell>
                      <TableCell className="py-3.5 text-center">
                        <span className="inline-flex items-center justify-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 font-mono">
                          Niveau {source.crawl_depth || 2}
                        </span>
                      </TableCell>
                      <TableCell className="py-3.5 text-center">
                        <Link href={`/dashboard/admin/sources/documents?parent_id=${source.id}`}>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 gap-1.5 text-xs font-semibold text-sovereign-700 hover:bg-sovereign-50"
                          >
                            <FileText className="w-3.5 h-3.5 text-sovereign-600" />
                            <span>{source.child_documents_count || 0} docs</span>
                            <ArrowRight className="w-3 h-3 opacity-60" />
                          </Button>
                        </Link>
                      </TableCell>
                      <TableCell className="py-3.5 text-xs text-slate-600">
                        <div className="flex flex-col gap-1">
                          <span className="text-slate-700">
                            {source.last_collection_at ? formatDateTime(source.last_collection_at) : 'Jamais'}
                          </span>
                          <div>{getRunBadge(source.last_collection_status)}</div>
                        </div>
                      </TableCell>
                      <TableCell className="py-3.5">{getStatusBadge(source.status)}</TableCell>
                      <TableCell className="py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="default"
                            size="sm"
                            className="h-8 px-2.5 gap-1.5 bg-sovereign-600 hover:bg-sovereign-700 text-white text-xs"
                            onClick={() => {
                              setCollectingSource(source);
                              setCrawlDepth(source.crawl_depth || 2);
                            }}
                            title="Lancer la collecte IA"
                          >
                            <Play className="w-3.5 h-3.5 fill-current" />
                            <span>Collecter</span>
                          </Button>
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8 text-slate-600 border-slate-200 hover:bg-slate-50"
                            title="Historique des runs"
                            onClick={() => setHistorySourceId(source.id)}
                          >
                            <History className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8 text-slate-600 border-slate-200 hover:bg-slate-50"
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
                            onClick={() => handleDelete(source)}
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
            <div className="text-center py-12 px-4">
              <Globe className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-900">Aucun portail trouvé</h3>
              <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
                Aucun portail ne correspond à vos filtres. Cliquez sur "Nouveau portail" pour configurer une autorité de régulation.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal: Create / Edit Portal */}
      <Dialog open={isCreateOpen || Boolean(editingSource)} onOpenChange={(open) => {
        if (!open) {
          setIsCreateOpen(false);
          setEditingSource(null);
        }
      }}>
        <DialogContent className="max-w-lg">
          <form onSubmit={handleSaveForm} className="space-y-4">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold text-slate-900">
                {editingSource ? 'Modifier le portail officiel' : 'Ajouter un portail officiel'}
              </DialogTitle>
              <DialogDescription className="text-sm text-slate-500">
                Configurez l'autorité juridique et l'URL racine que le crawler IA explorera pour télécharger et structurer les textes de loi.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3.5 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="title" className="text-xs font-semibold text-slate-700">Nom du portail / Institution</Label>
                <Input
                  id="title"
                  placeholder="ex: APDP Bénin - Protection des Données"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="authority" className="text-xs font-semibold text-slate-700">Autorité de régulation</Label>
                  <Input
                    id="authority"
                    placeholder="ex: APDP Bénin"
                    value={formData.authority}
                    onChange={(e) => setFormData({ ...formData, authority: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="country" className="text-xs font-semibold text-slate-700">Juridiction / Pays</Label>
                  <Select
                    value={formData.country_code}
                    onValueChange={(val) => setFormData({ ...formData, country_code: val })}
                  >
                    <SelectTrigger id="country">
                      <SelectValue placeholder="Choisir un pays" />
                    </SelectTrigger>
                    <SelectContent>
                      {COUNTRY_OPTIONS.filter((c) => c.value).map((c) => (
                        <SelectItem key={c.value} value={c.value}>
                          {c.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="url_official" className="text-xs font-semibold text-slate-700">URL officielle de départ</Label>
                <Input
                  id="url_official"
                  type="url"
                  placeholder="https://service.apdp.bj/"
                  value={formData.url_official}
                  onChange={(e) => setFormData({ ...formData, url_official: e.target.value })}
                  required
                />
                <p className="text-[11px] text-slate-400">Le robot naviguera sur ce domaine et découvrira les sections documentation, lois et PDF.</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="crawl_depth" className="text-xs font-semibold text-slate-700">Profondeur de crawl</Label>
                  <Select
                    value={String(formData.crawl_depth)}
                    onValueChange={(val) => setFormData({ ...formData, crawl_depth: Number(val) })}
                  >
                    <SelectTrigger id="crawl_depth">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">Niveau 1 (Page seule)</SelectItem>
                      <SelectItem value="2">Niveau 2 (Recommandé - Liens directs)</SelectItem>
                      <SelectItem value="3">Niveau 3 (Exploration approfondie)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="level" className="text-xs font-semibold text-slate-700">Niveau normatif par défaut</Label>
                  <Select
                    value={formData.level}
                    onValueChange={(val) => setFormData({ ...formData, level: val })}
                  >
                    <SelectTrigger id="level">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="loi">Loi</SelectItem>
                      <SelectItem value="décret">Décret</SelectItem>
                      <SelectItem value="règlement">Règlement</SelectItem>
                      <SelectItem value="décision">Décision</SelectItem>
                      <SelectItem value="guide">Guide</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsCreateOpen(false);
                  setEditingSource(null);
                }}
              >
                Annuler
              </Button>
              <Button type="submit" className="bg-sovereign-600 hover:bg-sovereign-700 text-white">
                {editingSource ? 'Mettre à jour' : 'Enregistrer le portail'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal: Confirm Trigger Collect */}
      <Dialog open={Boolean(collectingSource)} onOpenChange={(open) => !open && setCollectingSource(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-sovereign-600" />
              Lancer la collecte intelligente
            </DialogTitle>
            <DialogDescription className="text-sm text-slate-500">
              Le robot va explorer <strong className="text-slate-800">{collectingSource?.title}</strong>, télécharger les PDF officiels, les stocker dans le bucket MinIO S3 et faire extraire les articles et sanctions par l'IA.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <Label htmlFor="collect_depth" className="text-xs font-semibold text-slate-700">
              Sélectionnez la profondeur d'exploration :
            </Label>
            <Select value={String(crawlDepth)} onValueChange={(val) => setCrawlDepth(Number(val))}>
              <SelectTrigger id="collect_depth">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">Niveau 1 : Page racine seulement</SelectItem>
                <SelectItem value="2">Niveau 2 : Page racine + sous-menus / documentation (Recommandé)</SelectItem>
                <SelectItem value="3">Niveau 3 : Exploration profonde du portail</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-slate-400 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
              Tous les fichiers PDF découverts seront automatiquement rattachés à ce portail et consultables dans la bibliothèque juridique avec leur nom de fichier d'origine.
            </p>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCollectingSource(null)}>
              Annuler
            </Button>
            <Button
              onClick={handleTriggerCollect}
              disabled={collectSource.isPending}
              className="bg-sovereign-600 hover:bg-sovereign-700 text-white gap-2"
            >
              {collectSource.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              Démarrer le crawl
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal: Collection History */}
      <Dialog open={Boolean(historySourceId)} onOpenChange={(open) => !open && setHistorySourceId(undefined)}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <History className="w-5 h-5 text-slate-600" />
              Historique des collectes robotisées
            </DialogTitle>
            <DialogDescription className="text-sm text-slate-500">
              Traçabilité des explorations web, des téléchargements et des analyses IA réalisées.
            </DialogDescription>
          </DialogHeader>

          {isHistoryLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-sovereign-600" />
            </div>
          ) : collectionRuns && collectionRuns.length > 0 ? (
            <div className="space-y-3">
              {collectionRuns.map((run) => (
                <div key={run.id} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getRunBadge(run.status)}
                      <span className="text-xs text-slate-500 font-mono">
                        {run.started_at ? formatDateTime(run.started_at) : formatDateTime(run.requested_at)}
                      </span>
                    </div>
                    <span className="text-xs text-slate-400 capitalize">
                      Déclenchement: {run.trigger_type}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-1 text-xs">
                    <div className="bg-white p-2 rounded border border-slate-100">
                      <span className="text-slate-400 block">URLs scannées</span>
                      <span className="font-semibold text-slate-800">{run.discovered_urls_count || 0}</span>
                    </div>
                    <div className="bg-white p-2 rounded border border-slate-100">
                      <span className="text-slate-400 block">PDF téléchargés</span>
                      <span className="font-semibold text-emerald-700">{run.downloaded_files_count || 0}</span>
                    </div>
                    <div className="bg-white p-2 rounded border border-slate-100">
                      <span className="text-slate-400 block">Analysés par IA</span>
                      <span className="font-semibold text-purple-700">{run.ai_processed_count || 0}</span>
                    </div>
                  </div>

                  {run.error_message && (
                    <p className="text-xs text-rose-600 bg-rose-50 p-2 rounded border border-rose-200">
                      {run.error_message}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-sm text-slate-500">
              Aucune collecte n'a encore été effectuée pour ce portail.
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setHistorySourceId(undefined)}>
              Fermer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
