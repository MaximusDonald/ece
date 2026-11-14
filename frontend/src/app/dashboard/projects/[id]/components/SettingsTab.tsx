'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { useProject, useUpdateProject, useDeleteProject } from '@/hooks/useApi';
import { useState } from 'react';
import { Save, Trash2, AlertTriangle, CheckCircle } from 'lucide-react';

const SECTORS = [
  'FinTech', 'E-commerce', 'Services Numériques', 'Santé', 'Éducation',
  'Administration', 'Télécoms', 'Énergie', 'Transport', 'Autre',
];

const STATUS_OPTIONS = [
  { value: 'active', label: 'Actif' },
  { value: 'completed', label: 'Terminé' },
  { value: 'archived', label: 'Archivé' },
];

const REPRESENTED_ROLE_OPTIONS = [
  { value: 'entreprise', label: "L'entreprise / maître d'ouvrage" },
  { value: 'developpeur_engage', label: 'Un développeur engagé (salarié, stagiaire, freelance interne)' },
  { value: 'prestataire_externe', label: 'Un prestataire externe (évaluation de vos propres risques)' },
  { value: 'dpo_juriste', label: 'Un DPO / juriste / auditeur interne' },
  { value: 'autre', label: 'Autre (à préciser)' },
];

const TREATMENT_OPTIONS = [
  { value: 'data_protection', label: 'Protection des données personnelles' },
  { value: 'payment_services', label: 'Services de paiement / Monnaie électronique' },
  { value: 'ecommerce', label: 'Commerce électronique' },
  { value: 'cybersecurity', label: 'Cybersécurité' },
  { value: 'digital_identity', label: 'Identité numérique' },
  { value: 'data_retention', label: 'Conservation des données' },
  { value: 'subcontracting', label: 'Sous-traitance' },
  { value: 'incident_notification', label: 'Notification d\'incidents' },
  { value: 'aml_cft', label: 'Lutte contre le blanchiment (LCB/FT)' },
];

export function ProjectWorkspaceSettings({ projectId, project }: { projectId: string; project: any }) {
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();
  const [formData, setFormData] = useState({
    name: project.name,
    sector: project.sector,
    status: project.status,
    treatments: [...project.treatments],
    represented_entity_type: project.represented_entity_type || 'entreprise',
    represented_entity_other: project.represented_entity_other || '',
    represented_role_details: project.represented_role_details || '',
  });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.represented_entity_type === 'autre' && !formData.represented_entity_other.trim()) {
      setMessage({ type: 'error', text: "Veuillez préciser le rôle représenté lorsque 'Autre' est sélectionné." });
      return;
    }
    try {
      await updateProject.mutateAsync({
        id: projectId,
        data: {
          ...formData,
          represented_entity_other:
            formData.represented_entity_type === 'autre' ? formData.represented_entity_other.trim() : null,
          represented_role_details: formData.represented_role_details.trim() || null,
        },
      });
      setMessage({ type: 'success', text: 'Projet mis à jour avec succès' });
      setTimeout(() => setMessage(null), 3000);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Erreur lors de la mise à jour' });
    }
  };

  const handleDelete = async () => {
    try {
      await deleteProject.mutateAsync(projectId);
      // Redirect handled by router
    } catch (err) {
      setMessage({ type: 'error', text: 'Erreur lors de la suppression' });
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      {message && (
        <div className={cn('p-4 rounded-lg', message.type === 'success' ? 'bg-success-50 text-success-700' : 'bg-danger-50 text-danger-700')}>
          {message.text}
        </div>
      )}

      {/* Project Info */}
      <Card>
        <CardHeader>
          <CardTitle>Informations du projet</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Label htmlFor="name">Nom du projet *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="ex: StockOpti — Bénin"
                required
              />
            </div>

            <div>
              <Label>Pays cible</Label>
              <div className="mt-1">
                <Badge variant={project.country_code.toLowerCase() === 'bj' ? 'default' : 'secondary'} className="text-lg px-4 py-2">
                  {project.country_code.toUpperCase()}
                </Badge>
                <p className="text-sm text-slate-500 mt-1">Le pays ne peut pas être modifié après création.</p>
              </div>
            </div>

            <div>
              <Label htmlFor="sector">Secteur d'activité *</Label>
              <select
                id="sector"
                value={formData.sector}
                onChange={(e) => setFormData({ ...formData, sector: e.target.value })}
                className="input"
                required
              >
                <option value="">Sélectionnez un secteur</option>
                {SECTORS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div>
              <Label>Types de traitement / services</Label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                {TREATMENT_OPTIONS.map((opt) => (
                  <label key={opt.value} className="flex items-center gap-2 p-3 border rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
                    <input
                      type="checkbox"
                      checked={formData.treatments.includes(opt.value)}
                      onChange={(e) => setFormData({
                        ...formData,
                        treatments: e.target.checked
                          ? [...formData.treatments, opt.value]
                          : formData.treatments.filter(t => t !== opt.value)
                      })}
                      className="h-4 w-4 text-sovereign-500 border-slate-300 rounded focus:ring-sovereign-500"
                    />
                    <span className="text-sm text-slate-700">{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <Label htmlFor="status">Statut du projet</Label>
              <select
                id="status"
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="input"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div className="space-y-4 pt-4 border-t border-slate-100">
              <div>
                <Label htmlFor="represented_entity_type">Qui représentez-vous pour cette analyse ? *</Label>
                <select
                  id="represented_entity_type"
                  value={formData.represented_entity_type}
                  onChange={(e) => setFormData({ ...formData, represented_entity_type: e.target.value })}
                  className="input mt-1"
                  required
                >
                  {REPRESENTED_ROLE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {formData.represented_entity_type === 'autre' && (
                <div>
                  <Label htmlFor="represented_entity_other">Précisez le rôle représenté *</Label>
                  <Input
                    id="represented_entity_other"
                    value={formData.represented_entity_other}
                    onChange={(e) => setFormData({ ...formData, represented_entity_other: e.target.value })}
                    placeholder="ex: Investisseur, Partenaire bancaire..."
                    required
                  />
                </div>
              )}

              <div>
                <Label htmlFor="represented_role_details">Description détaillée du rôle (optionnel)</Label>
                <textarea
                  id="represented_role_details"
                  rows={3}
                  value={formData.represented_role_details}
                  onChange={(e) => setFormData({ ...formData, represented_role_details: e.target.value })}
                  placeholder="Précisez vos responsabilités ou la perspective souhaitée pour l'audit..."
                  className="input w-full mt-1"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
              <Button type="submit" disabled={updateProject.isPending}>
                {updateProject.isPending ? 'Enregistrement...' : 'Enregistrer les modifications'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-danger-200">
        <CardHeader>
          <CardTitle className="text-danger-600 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Zone de danger
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">Supprimer le projet</p>
              <p className="text-sm text-slate-500 mt-1">
                Cette action est irréversible. Tous les documents, analyses et rapports associés seront supprimés définitivement.
              </p>
            </div>
            <Button
              variant="destructive"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleteProject.isPending}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Supprimer le projet
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowDeleteConfirm(false)}>
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-slate-200">
              <h2 className="text-xl font-semibold text-danger-600 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Confirmer la suppression
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-slate-600">
                Êtes-vous sûr de vouloir supprimer <strong>"{project.name}"</strong> ?
                Cette action supprimera tous les documents, analyses et rapports associés et ne peut pas être annulée.
              </p>
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <Button variant="secondary" onClick={() => setShowDeleteConfirm(false)}>
                  Annuler
                </Button>
                <Button variant="destructive" onClick={handleDelete} disabled={deleteProject.isPending}>
                  {deleteProject.isPending ? 'Suppression...' : 'Supprimer définitivement'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { cn } from '@/lib/utils';