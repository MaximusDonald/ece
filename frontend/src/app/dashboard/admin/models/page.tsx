'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAdminModels, useCreateModel, useUpdateModel } from '@/hooks/useApi';
import { Plus, Save, X, Edit2, CheckCircle, AlertTriangle } from 'lucide-react';
import { useState } from 'react';

const PROVIDER_OPTIONS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
];

const MODEL_OPTIONS: Record<string, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
};

export default function AdminModelsPage() {
  const { data: models, isLoading, refetch } = useAdminModels();
  const createModel = useCreateModel();
  const updateModel = useUpdateModel();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    provider: 'openai',
    model: 'gpt-4o-mini',
    temperature: 0.1,
    max_tokens: 4000,
    system_prompt_version: 'v1',
    system_prompt: 'Tu es un expert juridique spécialisé en droit CEDEAO/UEMOA/OHADA et droit béninois. Réponds de manière précise, structurée et sourcée. Ne jamais inventer de références juridiques. Si tu ne sais pas, dis-le explicitement.',
    is_active: true,
    is_default: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await updateModel.mutateAsync({ id: editingId, data: formData });
      } else {
        await createModel.mutateAsync(formData);
      }
      setIsCreateOpen(false);
      setEditingId(null);
      resetForm();
      refetch();
    } catch (err) {
      alert('Erreur lors de l\'enregistrement');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      provider: 'openai',
      model: 'gpt-4o-mini',
      temperature: 0.1,
      max_tokens: 4000,
      system_prompt_version: 'v1',
      system_prompt: 'Tu es un expert juridique spécialisé en droit CEDEAO/UEMOA/OHADA et droit béninois. Réponds de manière précise, structurée et sourcée. Ne jamais inventer de références juridiques. Si tu ne sais pas, dis-le explicitement.',
      is_active: true,
      is_default: false,
    });
  };

  const handleEdit = (model: any) => {
    setEditingId(model.id);
    setFormData({ ...model });
    setIsCreateOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Modèles LLM</h1>
          <p className="page-subtitle">Configurez les modèles d'IA utilisés pour l'analyse et le RAG</p>
        </div>
        <Button onClick={() => { resetForm(); setIsCreateOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          Nouveau modèle
        </Button>
      </div>

      {/* Models Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
            </div>
          ) : models && models.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Fournisseur</TableHead>
                  <TableHead>Modèle</TableHead>
                  <TableHead>Température</TableHead>
                  <TableHead>Max tokens</TableHead>
                  <TableHead>Version prompt</TableHead>
                  <TableHead>Défaut</TableHead>
                  <TableHead>Actif</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {models.map((model) => (
                  <TableRow key={model.id}>
                    <TableCell className="font-medium">{model.name}</TableCell>
                    <TableCell>
                      <Badge variant={model.provider === 'openai' ? 'default' : 'secondary'}>
                        {model.provider.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{model.model}</TableCell>
                    <TableCell>{model.temperature}</TableCell>
                    <TableCell>{model.max_tokens}</TableCell>
                    <TableCell>{model.system_prompt_version}</TableCell>
                    <TableCell>
                      {model.is_default && <Badge variant="default">Défaut</Badge>}
                    </TableCell>
                    <TableCell>
                      <Badge variant={model.is_active ? 'conforme' : 'secondary'}>
                        {model.is_active ? 'Oui' : 'Non'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(model)}>
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucun modèle</h3>
              <p className="text-slate-500 mb-4">Configurez votre premier modèle LLM.</p>
              <Button onClick={() => { resetForm(); setIsCreateOpen(true); }}>
                <Plus className="h-4 w-4 mr-2" />
                Ajouter un modèle
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => { setIsCreateOpen(false); setEditingId(null); resetForm(); }}>
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold">{editingId ? 'Modifier le modèle' : 'Nouveau modèle LLM'}</h2>
              <button onClick={() => { setIsCreateOpen(false); setEditingId(null); resetForm(); }} className="text-slate-400 hover:text-slate-600">
                <X className="h-6 w-6" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="name">Nom *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="ex: OpenAI GPT-4o-mini (Default)"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="provider">Fournisseur *</Label>
                  <Select value={formData.provider} onValueChange={(v) => setFormData({ ...formData, provider: v, model: MODEL_OPTIONS[v][0] })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PROVIDER_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="model">Modèle *</Label>
                  <Select value={formData.model} onValueChange={(v) => setFormData({ ...formData, model: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MODEL_OPTIONS[formData.provider].map((m) => (
                        <SelectItem key={m} value={m}>{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="temperature">Température</Label>
                  <Input
                    id="temperature"
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={formData.temperature}
                    onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                    className="input"
                  />
                </div>
                <div>
                  <Label htmlFor="max_tokens">Max tokens</Label>
                  <Input
                    id="max_tokens"
                    type="number"
                    min="1"
                    value={formData.max_tokens}
                    onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })}
                    className="input"
                  />
                </div>
                <div>
                  <Label htmlFor="system_prompt_version">Version prompt système</Label>
                  <Input
                    id="system_prompt_version"
                    value={formData.system_prompt_version}
                    onChange={(e) => setFormData({ ...formData, system_prompt_version: e.target.value })}
                    className="input"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="system_prompt">Prompt système *</Label>
                <textarea
                  id="system_prompt"
                  value={formData.system_prompt}
                  onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                  className="input min-h-[200px] font-mono text-sm"
                  required
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label>Actif</Label>
                  <div className="mt-2">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                        className="h-4 w-4 text-sovereign-500 border-slate-300 rounded"
                      />
                      <span className="text-sm">Modèle actif</span>
                    </label>
                  </div>
                </div>
                <div>
                  <Label>Modèle par défaut</Label>
                  <div className="mt-2">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.is_default}
                        onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                        className="h-4 w-4 text-sovereign-500 border-slate-300 rounded"
                      />
                      <span className="text-sm">Utiliser comme modèle par défaut</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <Button type="button" variant="secondary" onClick={() => { setIsCreateOpen(false); setEditingId(null); resetForm(); }}>
                  Annuler
                </Button>
                <Button type="submit" disabled={createModel.isPending || updateModel.isPending}>
                  {createModel.isPending || updateModel.isPending ? 'Enregistrement...' : editingId ? 'Enregistrer' : 'Créer'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}