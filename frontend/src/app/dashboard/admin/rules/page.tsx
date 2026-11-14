'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAdminRules, useCreateRule, useUpdateRule } from '@/hooks/useApi';
import { Plus, Save, X, Edit2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from '@/hooks/use-toast';

const DOMAIN_OPTIONS = [
  { value: 'data_protection', label: 'Protection des données' },
  { value: 'payment_services', label: 'Services de paiement' },
  { value: 'ecommerce', label: 'E-commerce' },
  { value: 'cybersecurity', label: 'Cybersécurité' },
  { value: 'digital_identity', label: 'Identité numérique' },
  { value: 'data_retention', label: 'Conservation des données' },
  { value: 'subcontracting', label: 'Sous-traitance' },
  { value: 'incident_notification', label: 'Notification d\'incidents' },
  { value: 'aml_cft', label: 'LCB/FT' },
  { value: 'global', label: 'Global (tous domaines)' },
];

export default function AdminRulesPage() {
  const { data: rules, isLoading, refetch } = useAdminRules();
  const createRule = useCreateRule();
  const updateRule = useUpdateRule();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    domain: 'global',
    country_code: '',
    weight_critique: 1.0,
    weight_eleve: 0.7,
    weight_modere: 0.4,
    weight_a_surveiller: 0.1,
    weight_conforme: 0.0,
    confidence_threshold_high: 0.8,
    confidence_threshold_medium: 0.5,
    is_active: true,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await updateRule.mutateAsync({ id: editingId, data: formData });
      } else {
        await createRule.mutateAsync(formData);
      }
      setIsCreateOpen(false);
      setEditingId(null);
      resetForm();
      refetch();
    } catch (err) {
      toast({ title: 'Enregistrement impossible', description: 'La règle n’a pas pu être enregistrée. Vérifiez les champs puis réessayez.', variant: 'destructive' });
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      domain: 'global',
      country_code: '',
      weight_critique: 1.0,
      weight_eleve: 0.7,
      weight_modere: 0.4,
      weight_a_surveiller: 0.1,
      weight_conforme: 0.0,
      confidence_threshold_high: 0.8,
      confidence_threshold_medium: 0.5,
      is_active: true,
    });
  };

  const handleEdit = (rule: any) => {
    setEditingId(rule.id);
    setFormData({ ...rule });
    setIsCreateOpen(true);
  };

  const simulateRuleScore = (
    domainFindings: number[][],
    sanctionBonus: number,
  ): { raw: number; final: number; hasCritical: boolean } => {
    const weights = {
      critique: (Number(formData.weight_critique) || 0) * 25,
      eleve: (Number(formData.weight_eleve) || 0) * 20,
      modere: (Number(formData.weight_modere) || 0) * 12,
      surveiller: (Number(formData.weight_a_surveiller) || 0) * 5,
    };

    let raw = 0;
    let hasCritical = false;
    let hasNonConforme = false;

    for (const domainCounts of domainFindings) {
      const [c, e, m, s] = domainCounts;
      const list: number[] = [];
      for (let i = 0; i < c; i++) {
        list.push(weights.critique);
        hasCritical = true;
        hasNonConforme = true;
      }
      for (let i = 0; i < e; i++) {
        list.push(weights.eleve);
        hasNonConforme = true;
      }
      for (let i = 0; i < m; i++) {
        list.push(weights.modere);
        hasNonConforme = true;
      }
      for (let i = 0; i < s; i++) {
        list.push(weights.surveiller);
        hasNonConforme = true;
      }
      list.sort((a, b) => b - a);
      list.forEach((w, idx) => {
        raw += w * Math.pow(0.5, idx);
      });
    }

    raw += Math.min(25, sanctionBonus);
    if (!hasNonConforme) {
      return { raw: 0, final: 0, hasCritical: false };
    }
    const compressed = raw <= 70 ? raw : 70 + 30 * (1 - Math.exp(-(raw - 70) / 45));
    let finalScore = Math.min(100, Math.max(0, Math.round(compressed)));
    if (hasCritical && finalScore < 50) {
      finalScore = 50;
    }
    return { raw: Math.round(raw * 10) / 10, final: finalScore, hasCritical };
  };

  const simSingleCritical = simulateRuleScore([[1, 0, 0, 0]], 0);
  const simSameFacet = simulateRuleScore([[2, 0, 0, 0], [0, 1, 0, 0]], 8);
  const simMultiFacetHeavy = simulateRuleScore([[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]], 16);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Règles de scoring</h1>
          <p className="page-subtitle">Configurez les pondérations et seuils par domaine et pays</p>
        </div>
        <Button onClick={() => { resetForm(); setIsCreateOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          Nouvelle règle
        </Button>
      </div>

      {/* Stabilized Scoring Model Summary */}
      <Card className="border-sovereign-200 bg-sovereign-50/40">
        <CardContent className="pt-5 pb-4">
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold text-slate-900">
                Politique de calcul stabilisée (ECE)
              </h2>
              <Badge variant="outline" className="bg-white">
                Rendements décroissants + Compression &gt; 70
              </Badge>
            </div>
            <div className="grid gap-3 md:grid-cols-4 text-xs text-slate-700">
              <div className="rounded-lg bg-white p-3 border border-slate-200">
                <div className="font-semibold text-slate-900 mb-1">1. Poids de base</div>
                <p>Critique × 25 pts · Élevé × 20 pts · Modéré × 12 pts · À surveiller × 5 pts · Conforme × 0 pt.</p>
              </div>
              <div className="rounded-lg bg-white p-3 border border-slate-200">
                <div className="font-semibold text-slate-900 mb-1">2. Rendements décroissants</div>
                <p>Par facette juridique, les constats sont triés par gravité puis pondérés à 100 %, 50 %, 25 %, 12,5 %…</p>
              </div>
              <div className="rounded-lg bg-white p-3 border border-slate-200">
                <div className="font-semibold text-slate-900 mb-1">3. Sanctions dédupliquées</div>
                <p>+8 pts (pénal) ou +4 pts (admin) comptés une seule fois par article unique, plafonnés à +25 pts.</p>
              </div>
              <div className="rounded-lg bg-white p-3 border border-slate-200">
                <div className="font-semibold text-slate-900 mb-1">4. Plancher &amp; compression</div>
                <p>Plancher à 50/100 si un risque critique subsiste ; compression douce au-delà de 70/100.</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Rules Table */}
      <Card>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
            </div>
          ) : rules && rules.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Domaine</TableHead>
                  <TableHead>Pays</TableHead>
                  <TableHead>Pondérations (C/E/M/A/C)</TableHead>
                  <TableHead>Seuils confiance (H/M)</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <TableRow key={rule.id}>
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{rule.domain}</Badge>
                    </TableCell>
                    <TableCell>
                      {rule.country_code ? (
                        <Badge variant="default">{rule.country_code.toUpperCase()}</Badge>
                      ) : (
                        <Badge variant="secondary">Global</Badge>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      <div>
                        {rule.weight_critique}/{rule.weight_eleve}/{rule.weight_modere}/{rule.weight_a_surveiller}/{rule.weight_conforme}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        pts: {(rule.weight_critique * 25).toFixed(0)}/{(rule.weight_eleve * 20).toFixed(0)}/{(rule.weight_modere * 12).toFixed(0)}/{(rule.weight_a_surveiller * 5).toFixed(0)}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      H:{rule.confidence_threshold_high} M:{rule.confidence_threshold_medium}
                    </TableCell>
                    <TableCell>
                      <Badge variant={rule.is_active ? 'conforme' : 'secondary'}>
                        {rule.is_active ? 'Oui' : 'Non'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(rule)}>
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-12">
              <h3 className="text-lg font-medium text-slate-900 mb-2">Aucune règle</h3>
              <p className="text-slate-500 mb-4">Créez votre première règle de scoring.</p>
              <Button onClick={() => { resetForm(); setIsCreateOpen(true); }}>
                <Plus className="h-4 w-4 mr-2" />
                Créer une règle
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => { setIsCreateOpen(false); setEditingId(null); resetForm(); }}>
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold">{editingId ? 'Modifier la règle' : 'Nouvelle règle de scoring'}</h2>
              <button onClick={() => { setIsCreateOpen(false); setEditingId(null); resetForm(); }} className="text-slate-400 hover:text-slate-600">
                <X className="h-6 w-6" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="name">Nom de la règle *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="ex: Bénin Data Protection"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="domain">Domaine *</Label>
                  <Select value={formData.domain} onValueChange={(v) => setFormData({ ...formData, domain: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DOMAIN_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="country_code">Pays (vide = global)</Label>
                  <Select
                    value={formData.country_code || 'all'}
                    onValueChange={(v) => setFormData({ ...formData, country_code: v === 'all' ? '' : v })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Global" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Global</SelectItem>
                      <SelectItem value="BJ">Bénin</SelectItem>
                      <SelectItem value="SN">Sénégal</SelectItem>
                      <SelectItem value="CI">Côte d'Ivoire</SelectItem>
                      <SelectItem value="TG">Togo</SelectItem>
                      <SelectItem value="BF">Burkina Faso</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Active</Label>
                  <div className="mt-2">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                        className="h-4 w-4 text-sovereign-500 border-slate-300 rounded"
                      />
                      <span className="text-sm">Règle active</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-6">
                <h3 className="font-medium mb-4">Pondérations des niveaux de risque</h3>
                <div className="grid gap-4 md:grid-cols-5">
                  <div>
                    <Label htmlFor="weight_critique">Critique</Label>
                    <Input
                      id="weight_critique"
                      type="number"
                      step="0.1"
                      min="0"
                      value={formData.weight_critique}
                      onChange={(e) => setFormData({ ...formData, weight_critique: parseFloat(e.target.value) })}
                      className="input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="weight_eleve">Élevé</Label>
                    <Input
                      id="weight_eleve"
                      type="number"
                      step="0.1"
                      min="0"
                      value={formData.weight_eleve}
                      onChange={(e) => setFormData({ ...formData, weight_eleve: parseFloat(e.target.value) })}
                      className="input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="weight_modere">Modéré</Label>
                    <Input
                      id="weight_modere"
                      type="number"
                      step="0.1"
                      min="0"
                      value={formData.weight_modere}
                      onChange={(e) => setFormData({ ...formData, weight_modere: parseFloat(e.target.value) })}
                      className="input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="weight_a_surveiller">À surveiller</Label>
                    <Input
                      id="weight_a_surveiller"
                      type="number"
                      step="0.1"
                      min="0"
                      value={formData.weight_a_surveiller}
                      onChange={(e) => setFormData({ ...formData, weight_a_surveiller: parseFloat(e.target.value) })}
                      className="input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="weight_conforme">Conforme</Label>
                    <Input
                      id="weight_conforme"
                      type="number"
                      step="0.1"
                      min="0"
                      value={formData.weight_conforme}
                      onChange={(e) => setFormData({ ...formData, weight_conforme: parseFloat(e.target.value) })}
                      className="input"
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="text-sm font-semibold text-slate-900">
                    Aperçu du calcul stabilisé pour cette règle
                  </h4>
                  <span className="text-xs font-mono text-slate-600">
                    C:{((Number(formData.weight_critique) || 0) * 25).toFixed(1)} · E:{((Number(formData.weight_eleve) || 0) * 20).toFixed(1)} · M:{((Number(formData.weight_modere) || 0) * 12).toFixed(1)} · A:{((Number(formData.weight_a_surveiller) || 0) * 5).toFixed(1)} pts
                  </span>
                </div>
                <div className="grid gap-2 md:grid-cols-3 text-xs">
                  <div className="rounded bg-white p-2.5 border border-slate-200">
                    <div className="text-slate-500">1 Critique isolé (sans sanction)</div>
                    <div className="mt-1 font-semibold text-slate-900">
                      {simSingleCritical.final}/100{' '}
                      <span className="font-normal text-slate-500">(brut {simSingleCritical.raw} → plancher 50)</span>
                    </div>
                  </div>
                  <div className="rounded bg-white p-2.5 border border-slate-200">
                    <div className="text-slate-500">2 Critiques même facette + 1 Élevé + 1 pénal</div>
                    <div className="mt-1 font-semibold text-slate-900">
                      {simSameFacet.final}/100{' '}
                      <span className="font-normal text-slate-500">(brut {simSameFacet.raw})</span>
                    </div>
                  </div>
                  <div className="rounded bg-white p-2.5 border border-slate-200">
                    <div className="text-slate-500">3 Critiques multi-facettes + 2 pénales</div>
                    <div className="mt-1 font-semibold text-slate-900">
                      {simMultiFacetHeavy.final}/100{' '}
                      <span className="font-normal text-slate-500">(brut {simMultiFacetHeavy.raw}, compressé)</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-6">
                <h3 className="font-medium mb-4">Seuils de confiance</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="confidence_threshold_high">Seuil Haute confiance (≥)</Label>
                    <Input
                      id="confidence_threshold_high"
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={formData.confidence_threshold_high}
                      onChange={(e) => setFormData({ ...formData, confidence_threshold_high: parseFloat(e.target.value) })}
                      className="input"
                    />
                  </div>
                  <div>
                    <Label htmlFor="confidence_threshold_medium">Seuil Confiance moyenne (≥)</Label>
                    <Input
                      id="confidence_threshold_medium"
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={formData.confidence_threshold_medium}
                      onChange={(e) => setFormData({ ...formData, confidence_threshold_medium: parseFloat(e.target.value) })}
                      className="input"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <Button type="button" variant="secondary" onClick={() => { setIsCreateOpen(false); setEditingId(null); resetForm(); }}>
                  Annuler
                </Button>
                <Button type="submit" disabled={createRule.isPending || updateRule.isPending}>
                  {createRule.isPending || updateRule.isPending ? 'Enregistrement...' : editingId ? 'Enregistrer' : 'Créer'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
