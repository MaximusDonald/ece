'use client';

import { useMemo, useState, type FormEvent } from 'react';
import { AlertTriangle, CheckCircle, Edit2, Plus, Search, X } from 'lucide-react';
import { AxiosError } from 'axios';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAdminModelProviders, useAdminModels, useCreateModel, useUpdateModel } from '@/hooks/useApi';
import type { LLMModelConfig, LLMProvider } from '@/lib/api';
import { toast } from '@/hooks/use-toast';

type ModelForm = {
  name: string;
  provider: LLMProvider;
  model: string;
  temperature: number;
  max_tokens: number;
  system_prompt_version: string;
  system_prompt: string;
  is_default: boolean;
  rpm_limit?: number;
  tpm_limit?: number;
  rpd_limit?: number;
};

const emptyForm = (provider: LLMProvider = 'openai'): ModelForm => ({
  name: '',
  provider,
  model: '',
  temperature: 0.1,
  max_tokens: 4000,
  system_prompt_version: 'v1',
  system_prompt: 'You are a legal expert. Answer precisely and never invent legal references.',
  is_default: false,
  rpm_limit: undefined,
  tpm_limit: undefined,
  rpd_limit: undefined,
});

function getErrorMessage(error: unknown) {
  const detail = (error as AxiosError<{ detail?: unknown }>)?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        if (!item || typeof item !== 'object') return '';
        const issue = item as { loc?: unknown[]; msg?: unknown };
        const field = issue.loc?.filter((part) => part !== 'body').join('.');
        return [field, typeof issue.msg === 'string' ? issue.msg : 'Valeur invalide'].filter(Boolean).join(' : ');
      })
      .filter(Boolean)
      .join(' ; ') || 'Les données envoyées sont invalides.';
  }
  return 'La requête a échoué. Vérifiez les champs et réessayez.';
}

export default function AdminModelsPage() {
  const { data: models, isLoading, isError, refetch } = useAdminModels();
  const { data: providers, isLoading: providersLoading } = useAdminModelProviders();
  const createModel = useCreateModel();
  const updateModel = useUpdateModel();
  const [search, setSearch] = useState('');
  const [providerFilter, setProviderFilter] = useState('all');
  const [availabilityFilter, setAvailabilityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<LLMModelConfig | null>(null);
  const [form, setForm] = useState<ModelForm>(emptyForm());
  const availableProviders = providers?.filter((item) => item.available) ?? [];

  const providerLabels = useMemo(
    () => new Map((providers ?? []).map((item) => [item.provider, item.label])),
    [providers],
  );

  const filteredModels = (models ?? []).filter((item) => {
    const matchesName = `${item.name} ${item.model}`.toLowerCase().includes(search.toLowerCase());
    return matchesName
      && (providerFilter === 'all' || item.provider === providerFilter)
      && (availabilityFilter === 'all' || (availabilityFilter === 'available') === item.available)
      && (statusFilter === 'all' || (statusFilter === 'active') === item.is_active);
  });

  const startCreate = () => {
    const provider = availableProviders[0]?.provider ?? 'openai';
    const definition = providers?.find((item) => item.provider === provider);
    setEditingModel(null);
    setForm({ ...emptyForm(provider), model: definition?.default_model ?? '' });
    setIsFormOpen(true);
  };

  const startEdit = (model: LLMModelConfig) => {
    setEditingModel(model);
    setForm({
      name: model.name,
      provider: model.provider,
      model: model.model,
      temperature: model.temperature,
      max_tokens: model.max_tokens,
      system_prompt_version: model.system_prompt_version,
      system_prompt: model.system_prompt,
      is_default: model.is_default,
      rpm_limit: model.rpm_limit ?? undefined,
      tpm_limit: model.tpm_limit ?? undefined,
      rpd_limit: model.rpd_limit ?? undefined,
    });
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
    setEditingModel(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      if (editingModel) {
        await updateModel.mutateAsync({
          id: editingModel.id,
          data: {
            model: form.model,
            temperature: form.temperature,
            max_tokens: form.max_tokens,
            system_prompt_version: form.system_prompt_version,
            system_prompt: form.system_prompt,
            is_default: form.is_default,
            rpm_limit: form.rpm_limit ?? null,
            tpm_limit: form.tpm_limit ?? null,
            rpd_limit: form.rpd_limit ?? null,
          },
        });
        toast({ title: 'Modèle modifié', description: 'La configuration a été enregistrée.' });
      } else {
        await createModel.mutateAsync({ ...form, is_active: true });
        toast({ title: 'Modèle vérifié et ajouté', description: 'Le test fournisseur a réussi.' });
      }
      closeForm();
      refetch();
    } catch (error) {
      toast({
        title: editingModel ? 'Modification impossible' : 'Test ou ajout impossible',
        description: getErrorMessage(error),
        variant: 'destructive',
      });
    }
  };

  const toggleModel = async (model: LLMModelConfig) => {
    if (!model.available) return;
    try {
      await updateModel.mutateAsync({ id: model.id, data: { is_active: !model.is_active } });
      toast({
        title: model.is_active ? 'Modèle désactivé' : 'Modèle activé',
        description: model.is_active ? 'Les appels en cours ne sont pas interrompus.' : 'Il peut maintenant participer au choix et au fallback.',
      });
    } catch (error) {
      toast({ title: 'Activation impossible', description: getErrorMessage(error), variant: 'destructive' });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="page-title">Modèles LLM</h1>
          <p className="page-subtitle">Disponibilité des fournisseurs, modèles actifs et ordre de secours.</p>
        </div>
        <Button onClick={startCreate} disabled={providersLoading || availableProviders.length === 0}>
          <Plus className="h-4 w-4" /> Nouveau modèle
        </Button>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Fournisseurs déclarés</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {(providers ?? []).map((provider) => (
            <Badge key={provider.provider} variant={provider.available ? 'conforme' : 'secondary'}>
              {provider.label} · {provider.available ? 'Available' : 'Non disponible'}
            </Badge>
          ))}
          {providersLoading && <span className="text-sm text-slate-500">Vérification des fournisseurs…</span>}
          {!providersLoading && !availableProviders.length && (
            <p className="flex items-center gap-2 text-sm text-amber-700"><AlertTriangle className="h-4 w-4" />Aucune clé fournisseur configurée. L’ajout et l’activation sont désactivés.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Filtres</CardTitle></CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input aria-label="Rechercher un modèle" placeholder="Nom ou identifiant du modèle" value={search} onChange={(event) => setSearch(event.target.value)} className="pl-9" />
          </div>
          <Select value={providerFilter} onValueChange={setProviderFilter}>
            <SelectTrigger aria-label="Filtrer par fournisseur"><SelectValue placeholder="Tous les fournisseurs" /></SelectTrigger>
            <SelectContent><SelectItem value="all">Tous les fournisseurs</SelectItem>{(providers ?? []).map((item) => <SelectItem key={item.provider} value={item.provider}>{item.label}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={availabilityFilter} onValueChange={setAvailabilityFilter}>
            <SelectTrigger aria-label="Filtrer par disponibilité"><SelectValue placeholder="Toutes les disponibilités" /></SelectTrigger>
            <SelectContent><SelectItem value="all">Toutes les disponibilités</SelectItem><SelectItem value="available">Available</SelectItem><SelectItem value="unavailable">Non disponible</SelectItem></SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger aria-label="Filtrer par statut"><SelectValue placeholder="Tous les statuts" /></SelectTrigger>
            <SelectContent><SelectItem value="all">Tous les statuts</SelectItem><SelectItem value="active">Actifs</SelectItem><SelectItem value="inactive">Inactifs</SelectItem></SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="overflow-x-auto pt-6">
          {isLoading ? (
            <div className="flex justify-center py-12" role="status" aria-label="Chargement des modèles"><div className="h-8 w-8 animate-spin rounded-full border-b-2 border-sovereign-500" /></div>
          ) : isError ? (
            <div className="py-10 text-center"><AlertTriangle className="mx-auto mb-2 h-6 w-6 text-amber-600" /><p>Impossible de charger les modèles.</p><Button variant="outline" className="mt-3" onClick={() => refetch()}>Réessayer</Button></div>
          ) : filteredModels.length ? (
            <Table>
              <TableHeader><TableRow>
                <TableHead>Nom / modèle</TableHead><TableHead>Fournisseur</TableHead><TableHead>Disponibilité</TableHead>
                <TableHead>Débit (RPM / TPM / RPD)</TableHead>
                <TableHead>Température</TableHead><TableHead>Tokens max.</TableHead><TableHead>Prompt</TableHead>
                <TableHead>Défaut</TableHead><TableHead>Statut</TableHead><TableHead>Activer</TableHead><TableHead className="text-right">Actions</TableHead>
              </TableRow></TableHeader>
              <TableBody>{filteredModels.map((model) => (
                <TableRow key={model.id}>
                  <TableCell><div className="font-medium">{model.name}</div><code className="text-xs text-slate-500">{model.model}</code></TableCell>
                  <TableCell>{providerLabels.get(model.provider) ?? model.provider}</TableCell>
                  <TableCell><Badge variant={model.available ? 'conforme' : 'secondary'}>{model.available ? 'Available' : 'Non disponible'}</Badge></TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-0.5 text-xs">
                      <span className="font-semibold text-slate-800">
                        {model.rpm_limit ?? '—'} <span className="font-normal text-slate-400">RPM</span>
                      </span>
                      <span className="text-slate-500">
                        {model.tpm_limit ? `${Math.round(model.tpm_limit / 1000)}k` : '—'} <span className="text-slate-400">TPM</span> · {model.rpd_limit ?? '—'} <span className="text-slate-400">RPD</span>
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>{model.temperature}</TableCell><TableCell>{model.max_tokens}</TableCell><TableCell>{model.system_prompt_version}</TableCell>
                  <TableCell>{model.is_default ? <Badge>Défaut</Badge> : <span className="text-slate-400">—</span>}</TableCell>
                  <TableCell>{model.is_active ? 'Actif' : 'Inactif'}</TableCell>
                  <TableCell>
                    <button
                      type="button" role="switch" aria-checked={model.is_active} aria-label={`${model.is_active ? 'Désactiver' : 'Activer'} ${model.name}`}
                      disabled={(!model.available && !model.is_active) || updateModel.isPending}
                      onClick={() => void toggleModel(model)}
                      title={!model.available ? 'Ajoutez une clé API pour activer ce modèle.' : undefined}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sovereign-500 disabled:cursor-not-allowed disabled:opacity-40 ${model.is_active ? 'bg-sovereign-600' : 'bg-slate-300'}`}
                    ><span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${model.is_active ? 'translate-x-6' : 'translate-x-1'}`} /></button>
                  </TableCell>
                  <TableCell className="text-right"><Button variant="ghost" size="icon" aria-label={`Modifier ${model.name}`} onClick={() => startEdit(model)}><Edit2 className="h-4 w-4" /></Button></TableCell>
                </TableRow>
              ))}</TableBody>
            </Table>
          ) : (
            <div className="py-12 text-center text-sm text-slate-500">Aucun modèle ne correspond aux filtres.</div>
          )}
        </CardContent>
      </Card>

      {isFormOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) closeForm(); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="model-form-title" className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-xl">
            <header className="flex items-center justify-between border-b p-5"><h2 id="model-form-title" className="text-lg font-semibold">{editingModel ? 'Modifier le modèle' : 'Nouveau modèle'}</h2><Button type="button" variant="ghost" size="icon" onClick={closeForm} aria-label="Fermer"><X className="h-5 w-5" /></Button></header>
            <form onSubmit={handleSubmit} className="space-y-5 p-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <div><Label htmlFor="model-name">Nom</Label><Input id="model-name" required value={form.name} disabled={Boolean(editingModel)} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Ex. Modèle de secours juridique" /></div>
                <div><Label htmlFor="model-provider">Fournisseur</Label><Select disabled={Boolean(editingModel)} value={form.provider} onValueChange={(value) => { const provider = value as LLMProvider; const item = providers?.find((entry) => entry.provider === provider); setForm({ ...form, provider, model: item?.default_model ?? '' }); }}><SelectTrigger id="model-provider"><SelectValue /></SelectTrigger><SelectContent>{availableProviders.map((item) => <SelectItem key={item.provider} value={item.provider}>{item.label}</SelectItem>)}</SelectContent></Select></div>
                <div className="sm:col-span-2"><Label htmlFor="model-id">Identifiant modèle</Label><Input id="model-id" required value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} placeholder="Identifiant accepté par le fournisseur" /><p className="mt-1 text-xs text-slate-500">Le backend effectue un appel de test court avant d’enregistrer un nouveau modèle.</p></div>
                <div><Label htmlFor="temperature">Température</Label><Input id="temperature" type="number" step="0.1" min="0" max="2" value={form.temperature} onChange={(event) => setForm({ ...form, temperature: Number(event.target.value) })} /></div>
                <div><Label htmlFor="max-tokens">Tokens maximum</Label><Input id="max-tokens" type="number" min="1" value={form.max_tokens} onChange={(event) => setForm({ ...form, max_tokens: Number(event.target.value) })} /></div>
                <div className="sm:col-span-2"><Label htmlFor="prompt-version">Version du prompt système</Label><Input id="prompt-version" value={form.system_prompt_version} onChange={(event) => setForm({ ...form, system_prompt_version: event.target.value })} /></div>
                <div className="sm:col-span-2"><Label htmlFor="system-prompt">Prompt système</Label><textarea id="system-prompt" required value={form.system_prompt} onChange={(event) => setForm({ ...form, system_prompt: event.target.value })} className="input min-h-36 w-full rounded-lg border border-slate-300 p-3 text-sm" /></div>
                
                <div className="sm:col-span-2 rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                  <div className="mb-2">
                    <Label className="text-xs font-semibold uppercase tracking-wider text-slate-700">Limites de débit strictes (Protection Quotas &amp; Fallback)</Label>
                    <p className="text-xs text-slate-500">Configurez les limites officielles ou recommandées pour éviter les erreurs HTTP 429 et router automatiquement vers les modèles disponibles.</p>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <Label htmlFor="rpm-limit" className="text-xs">RPM (Req/min)</Label>
                      <Input
                        id="rpm-limit"
                        type="number"
                        min="1"
                        placeholder="Ex: 15"
                        value={form.rpm_limit ?? ''}
                        onChange={(e) => setForm({ ...form, rpm_limit: e.target.value ? Number(e.target.value) : undefined })}
                      />
                    </div>
                    <div>
                      <Label htmlFor="tpm-limit" className="text-xs">TPM (Tokens/min)</Label>
                      <Input
                        id="tpm-limit"
                        type="number"
                        min="1000"
                        step="1000"
                        placeholder="Ex: 250000"
                        value={form.tpm_limit ?? ''}
                        onChange={(e) => setForm({ ...form, tpm_limit: e.target.value ? Number(e.target.value) : undefined })}
                      />
                    </div>
                    <div>
                      <Label htmlFor="rpd-limit" className="text-xs">RPD (Req/jour)</Label>
                      <Input
                        id="rpd-limit"
                        type="number"
                        min="1"
                        placeholder="Ex: 500"
                        value={form.rpd_limit ?? ''}
                        onChange={(e) => setForm({ ...form, rpd_limit: e.target.value ? Number(e.target.value) : undefined })}
                      />
                    </div>
                  </div>
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_default} onChange={(event) => setForm({ ...form, is_default: event.target.checked })} /><CheckCircle className="h-4 w-4 text-slate-500" />Définir comme modèle prioritaire</label>
              <footer className="flex justify-end gap-2 border-t pt-4"><Button type="button" variant="outline" onClick={closeForm}>Annuler</Button><Button type="submit" disabled={createModel.isPending || updateModel.isPending || (!editingModel && !availableProviders.some((item) => item.provider === form.provider))}>{createModel.isPending ? 'Test du fournisseur…' : updateModel.isPending ? 'Enregistrement…' : editingModel ? 'Enregistrer' : 'Tester et créer'}</Button></footer>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
