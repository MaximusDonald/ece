'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAdminSources, useAdminSourceCollections, useCollectSource, useCreateSource, useUpdateSource } from '@/hooks/useApi';
import { Plus, Search, CheckCircle, AlertTriangle, Clock, ExternalLink, History, Loader2, Play } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';
import { useState } from 'react';
import { toast } from '@/hooks/use-toast';

const STATUS_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'verified', label: 'Vérifiée' },
  { value: 'to_verify', label: 'À vérifier' },
  { value: 'replaced', label: 'Remplacée' },
  { value: 'archived', label: 'Archivée' },
  { value: 'disputed', label: 'Contestée' },
  { value: 'unofficial', label: 'Non officielle' },
];

const LEVEL_OPTIONS = [
  { value: '', label: 'Tous les niveaux' },
  { value: 'loi', label: 'Loi' },
  { value: 'décret', label: 'Décret' },
  { value: 'règlement', label: 'Règlement' },
  { value: 'directive', label: 'Directive' },
  { value: 'acte', label: 'Acte' },
  { value: 'instruction', label: 'Instruction' },
  { value: 'décision', label: 'Décision' },
  { value: 'recommandation', label: 'Recommandation' },
  { value: 'formulaire', label: 'Formulaire' },
  { value: 'guide', label: 'Guide' },
];

const COUNTRY_OPTIONS = [
  { value: '', label: 'Tous les pays' },
  { value: 'BJ', label: 'Bénin' },
  { value: 'SN', label: 'Sénégal' },
  { value: 'CI', label: "Côte d'Ivoire" },
  { value: 'TG', label: 'Togo' },
  { value: 'BF', label: 'Burkina Faso' },
  { value: 'NE', label: 'Niger' },
  { value: 'ML', label: 'Mali' },
  { value: 'GN', label: 'Guinée' },
  { value: 'GW', label: 'Guinée-Bissau' },
  { value: 'CV', label: 'Cap-Vert' },
  { value: 'GH', label: 'Ghana' },
  { value: 'NG', label: 'Nigéria' },
  { value: 'LR', label: 'Libéria' },
  { value: 'SL', label: 'Sierra Leone' },
  { value: 'GM', label: 'Gambie' },
];

export default function AdminSourcesPage() {
  const { data: sources, isLoading, refetch } = useAdminSources();
  const createSource = useCreateSource();
  const updateSource = useUpdateSource();
  const collectSource = useCollectSource();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [historySourceId, setHistorySourceId] = useState<string | undefined>();
  const [editData, setEditData] = useState<Record<string, any>>({});
  const [filters, setFilters] = useState({
    status: '',
    country_code: '',
    level: '',
    search: '',
  });
  const { data: collectionRuns, isLoading: isHistoryLoading } = useAdminSourceCollections(historySourceId);

  const filteredSources = sources?.filter(s => {
    const matchesStatus = !filters.status || s.status === filters.status;
    const matchesCountry = !filters.country_code || s.country_code === filters.country_code;
    const matchesLevel = !filters.level || s.level === filters.level;
    const matchesSearch = !filters.search || 
      s.title.toLowerCase().includes(filters.search.toLowerCase()) ||
      s.authority.toLowerCase().includes(filters.search.toLowerCase()) ||
      s.article_ref.toLowerCase().includes(filters.search.toLowerCase());
    return matchesStatus && matchesCountry && matchesLevel && matchesSearch;
  }) || [];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'verified': return <Badge variant="conforme"><CheckCircle className="h-3 w-3 mr-1" />Vérifiée</Badge>;
      case 'to_verify': return <Badge variant="a_surveiller"><Clock className="h-3 w-3 mr-1" />À vérifier</Badge>;
      case 'replaced': return <Badge variant="modere">Remplacée</Badge>;
      case 'archived': return <Badge variant="secondary">Archivée</Badge>;
      case 'disputed': return <Badge variant="critique">Contestée</Badge>;
      case 'unofficial': return <Badge variant="warning">Non officielle</Badge>;
      default: return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getLevelBadge = (level: string) => {
    return <Badge variant="outline" className="text-xs">{level}</Badge>;
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!String(editData.content_text || '').trim() && !editData.collection_enabled) {
      toast({ title: 'Contenu manquant', description: 'Collez un texte initial ou activez la collecte depuis l’URL officielle.', variant: 'destructive' });
      return;
    }
    try {
      await createSource.mutateAsync(editData);
      setIsCreateOpen(false);
      setEditData({});
      refetch();
    } catch (err) {
      toast({ title: 'Création impossible', description: 'La source juridique n’a pas pu être créée.', variant: 'destructive' });
    }
  };

  const handleUpdate = async (id: string) => {
    try {
      await updateSource.mutateAsync({ id, data: editData });
      setEditingId(null);
      setEditData({});
      refetch();
    } catch (err) {
      toast({ title: 'Mise à jour impossible', description: 'La source juridique n’a pas pu être modifiée.', variant: 'destructive' });
    }
  };

  const handleCollect = async (id: string) => {
    try {
      await collectSource.mutateAsync(id);
      setHistorySourceId(id);
      toast({ title: 'Collecte démarrée', description: 'Consultez l’historique pour son résultat.' });
      refetch();
    } catch (err) {
      toast({ title: 'Collecte impossible', description: 'Vérifiez que l’URL pointe vers un document HTML ou PDF public en HTTPS.', variant: 'destructive' });
    }
  };

  const collectionBadge = (status?: string | null) => {
    if (status === 'running' || status === 'queued') return <Badge variant="a_surveiller">{status === 'queued' ? 'En attente' : 'En cours'}</Badge>;
    if (status === 'succeeded') return <Badge variant="conforme">Mis à jour</Badge>;
    if (status === 'unchanged') return <Badge variant="secondary">Inchangée</Badge>;
    if (status === 'failed') return <Badge variant="critique">Échec</Badge>;
    return <span className="text-slate-400">Jamais collectée</span>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Sources juridiques</h1>
          <p className="page-subtitle">Gérez le corpus juridique : validation, obsolescence, intégrité</p>
        </div>
        <Button onClick={() => { setEditData({}); setIsCreateOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          Ajouter une source
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Rechercher par titre, autorité, article..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="pl-10"
              />
            </div>
            <Select value={filters.status} onValueChange={(v) => setFilters({ ...filters, status: v })}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Statut" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filters.country_code} onValueChange={(v) => setFilters({ ...filters, country_code: v })}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Pays" />
              </SelectTrigger>
              <SelectContent>
                {COUNTRY_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filters.level} onValueChange={(v) => setFilters({ ...filters, level: v })}>
              <SelectTrigger className="w-full sm:w-[180px]">
                <SelectValue placeholder="Niveau" />
              </SelectTrigger>
              <SelectContent>
                {LEVEL_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Sources Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
            </div>
          ) : filteredSources.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Titre</TableHead>
                  <TableHead>Autorité</TableHead>
                  <TableHead>Pays</TableHead>
                  <TableHead>Niveau</TableHead>
                  <TableHead>Article</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Dernière collecte</TableHead>
                  <TableHead>Hash</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSources.map((source) => (
                  <TableRow key={source.id}>
                    <TableCell className="max-w-[300px] truncate">
                      {editingId === source.id ? (
                        <Input
                          value={editData.title || source.title}
                          onChange={(e) => setEditData({ ...editData, title: e.target.value })}
                          className="text-sm"
                        />
                      ) : (
                        <span className="font-medium text-slate-900 truncate block">{source.title}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {editingId === source.id ? (
                        <Input
                          value={editData.authority || source.authority}
                          onChange={(e) => setEditData({ ...editData, authority: e.target.value })}
                          className="text-sm"
                        />
                      ) : (
                        source.authority
                      )}
                    </TableCell>
                    <TableCell>
                      {source.country_code ? (
                        <Badge variant="default">{source.country_code.toUpperCase()}</Badge>
                      ) : (
                        <Badge variant="secondary">Supranational</Badge>
                      )}
                    </TableCell>
                    <TableCell>{getLevelBadge(source.level)}</TableCell>
                    <TableCell>
                      {editingId === source.id ? (
                        <Input
                          value={editData.article_ref || source.article_ref}
                          onChange={(e) => setEditData({ ...editData, article_ref: e.target.value })}
                          className="text-sm"
                        />
                      ) : (
                        <span className="font-mono text-sm">{source.article_ref}</span>
                      )}
                    </TableCell>
                    <TableCell>{getStatusBadge(source.status)}</TableCell>
                    <TableCell className="text-sm text-slate-500">
                      <div>{source.last_collection_at ? formatDateTime(source.last_collection_at) : 'Jamais'}</div>
                      <div className="mt-1">{collectionBadge(source.last_collection_status)}</div>
                      {source.collection_enabled && <div className="mt-1 text-xs text-slate-400">Hebdomadaire activée</div>}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-500 max-w-[100px] truncate">
                      {source.content_hash.slice(0, 16)}...
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {editingId === source.id ? (
                          <>
                            <Button variant="ghost" size="icon" onClick={() => handleUpdate(source.id)}>
                              <CheckCircle className="h-4 w-4 text-success-600" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => { setEditingId(null); setEditData({}); }}>
                              <AlertTriangle className="h-4 w-4 text-slate-400" />
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button variant="ghost" size="icon" onClick={() => { setEditingId(source.id); setEditData({ ...source }); }}>
                              <ExternalLink className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" title="Collecter maintenant" onClick={() => handleCollect(source.id)} disabled={collectSource.isPending}>
                              {collectSource.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                            </Button>
                            <Button variant="ghost" size="icon" title="Historique des collectes" onClick={() => setHistorySourceId(source.id)}>
                              <History className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <div className="h-12 w-12 text-slate-300 mx-auto mb-4">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucune source</h3>
              <p className="text-slate-500 mb-4">Ajoutez votre première source juridique au corpus.</p>
              <Button onClick={() => { setEditData({}); setIsCreateOpen(true); }}>
                <Plus className="h-4 w-4 mr-2" />
                Ajouter une source
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {historySourceId && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Historique des collectes — {sources?.find((item) => item.id === historySourceId)?.title}</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setHistorySourceId(undefined)}>Fermer</Button>
          </CardHeader>
          <CardContent>
            {isHistoryLoading ? <div className="py-4 text-sm text-slate-500">Chargement de l’historique…</div> : !collectionRuns?.length ? (
              <p className="py-4 text-sm text-slate-500">Aucune collecte enregistrée.</p>
            ) : (
              <div className="space-y-3">
                {collectionRuns.map((run) => (
                  <div key={run.id} className="rounded-lg border border-slate-200 p-4 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">{collectionBadge(run.status)}<span>{run.trigger_type === 'scheduled' ? 'Automatique' : 'Manuelle'}</span></div>
                      <span className="text-slate-500">Demandée le {formatDateTime(run.requested_at)}</span>
                    </div>
                    {run.started_at && <p className="mt-1 text-xs text-slate-500">Démarrée le {formatDateTime(run.started_at)}{run.finished_at ? ` · terminée le ${formatDateTime(run.finished_at)}` : ''}</p>}
                    <p className="mt-2 text-slate-600">{run.changed === true ? 'Le texte a changé; l’embedding a été recalculé.' : run.changed === false ? 'Le texte est inchangé; aucun embedding recalculé.' : 'Résultat non disponible.'}</p>
                    {(run.previous_hash || run.collected_hash) && <p className="mt-1 break-all font-mono text-xs text-slate-500">Hash : {run.previous_hash?.slice(0, 12) || '—'} → {run.collected_hash?.slice(0, 12) || '—'}</p>}
                    {run.http_status_code && <p className="mt-1 text-xs text-slate-500">Réponse HTTP {run.http_status_code}</p>}
                    {run.error_message && <p role="alert" className="mt-2 rounded bg-rose-50 p-2 text-rose-800">{run.error_message}</p>}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Modal */}
      {(isCreateOpen || editingId) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => { setIsCreateOpen(false); setEditingId(null); setEditData({}); }}>
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold">{editingId ? 'Modifier la source' : 'Nouvelle source juridique'}</h2>
              <button onClick={() => { setIsCreateOpen(false); setEditingId(null); setEditData({}); }} className="text-slate-400 hover:text-slate-600">
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <form onSubmit={editingId ? () => handleUpdate(editingId) : handleCreate} className="p-6 space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="title">Titre *</Label>
                  <Input
                    id="title"
                    value={editData.title || ''}
                    onChange={(e) => setEditData({ ...editData, title: e.target.value })}
                    placeholder="ex: Loi n°2017-20 portant Code du numérique"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="authority">Autorité émettrice *</Label>
                  <Input
                    id="authority"
                    value={editData.authority || ''}
                    onChange={(e) => setEditData({ ...editData, authority: e.target.value })}
                    placeholder="ex: Assemblée nationale du Bénin"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="country_code">Pays</Label>
                  <Select value={editData.country_code || ''} onValueChange={(v) => setEditData({ ...editData, country_code: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionnez (vide = supranational)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Supranational (CEDEAO, UEMOA, OHADA, BCEAO)</SelectItem>
                      {COUNTRY_OPTIONS.filter(o => o.value).map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="level">Niveau juridique *</Label>
                  <Select value={editData.level || ''} onValueChange={(v) => setEditData({ ...editData, level: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionnez" />
                    </SelectTrigger>
                    <SelectContent>
                      {LEVEL_OPTIONS.filter(o => o.value).map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="article_ref">Référence d'article *</Label>
                  <Input
                    id="article_ref"
                    value={editData.article_ref || ''}
                    onChange={(e) => setEditData({ ...editData, article_ref: e.target.value })}
                    placeholder="ex: Articles 1-25"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="url_official">URL officielle *</Label>
                  <Input
                    id="url_official"
                    type="url"
                    value={editData.url_official || ''}
                    onChange={(e) => setEditData({ ...editData, url_official: e.target.value })}
                    placeholder="https://..."
                    required
                  />
                </div>
                <div className="md:col-span-2">
                  <Label htmlFor="content_text">Texte de référence initial (facultatif si la collecte est activée)</Label>
                  <textarea
                    id="content_text"
                    value={editData.content_text || ''}
                    onChange={(e) => setEditData({ ...editData, content_text: e.target.value })}
                    placeholder="Collez le texte ou laissez vide pour le récupérer depuis l’URL officielle..."
                    className="input min-h-[200px] font-mono text-sm"
                  />
                  <p className="mt-1 text-xs text-slate-500">L’URL doit pointer directement vers une page HTML ou un PDF public en HTTPS; les autres pages du site ne sont pas explorées.</p>
                </div>
                <div className="md:col-span-2 rounded-lg border border-slate-200 p-4">
                  <label className="flex items-start gap-3 text-sm font-medium text-slate-800">
                    <input type="checkbox" checked={Boolean(editData.collection_enabled)} onChange={(e) => setEditData({ ...editData, collection_enabled: e.target.checked })} className="mt-1" />
                    Activer la collecte automatique hebdomadaire
                  </label>
                  <p className="ml-6 mt-1 text-xs text-slate-500">Les URL activées sont vérifiées chaque lundi à 03 h, heure du Bénin. Vous pouvez aussi lancer une collecte manuelle depuis la liste.</p>
                </div>
                <div>
                  <Label htmlFor="status">Statut</Label>
                  <Select value={editData.status || 'to_verify'} onValueChange={(v) => setEditData({ ...editData, status: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STATUS_OPTIONS.filter(o => o.value).map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="effective_date">Date d'entrée en vigueur</Label>
                  <Input
                    id="effective_date"
                    type="date"
                    value={editData.effective_date ? editData.effective_date.split('T')[0] : ''}
                    onChange={(e) => setEditData({ ...editData, effective_date: e.target.value })}
                    className="input"
                  />
                </div>
                <div>
                  <Label htmlFor="abrogated_date">Date d'abrogation (si applicable)</Label>
                  <Input
                    id="abrogated_date"
                    type="date"
                    value={editData.abrogated_date ? editData.abrogated_date.split('T')[0] : ''}
                    onChange={(e) => setEditData({ ...editData, abrogated_date: e.target.value })}
                    className="input"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <Button type="button" variant="secondary" onClick={() => { setIsCreateOpen(false); setEditingId(null); setEditData({}); }}>
                  Annuler
                </Button>
                <Button type="submit" disabled={createSource.isPending || updateSource.isPending}>
                  {createSource.isPending || updateSource.isPending ? 'Enregistrement...' : editingId ? 'Enregistrer' : 'Créer'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
