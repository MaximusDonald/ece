'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { useContextDocument, useUpdateContextDocument } from '@/hooks/useApi';
import { toast } from '@/hooks/use-toast';
import { FileText, Loader2, Save, RefreshCw, X } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';

export function ContextDocumentModal({
  projectId,
  onClose,
}: {
  projectId: string;
  onClose: () => void;
}) {
  const { data: contextDoc, isLoading } = useContextDocument(projectId);
  const updateMutation = useUpdateContextDocument(projectId);
  const [markdown, setMarkdown] = useState('');

  useEffect(() => {
    if (contextDoc?.markdown !== undefined) {
      setMarkdown(contextDoc.markdown);
    } else if (!isLoading && !contextDoc) {
      setMarkdown('# Contexte complémentaire du projet\n\n- ');
    }
  }, [contextDoc, isLoading]);

  const handleSave = async (triggerReportUpdate: boolean) => {
    try {
      await updateMutation.mutateAsync({
        markdown,
        trigger_report_update: triggerReportUpdate,
      });
      toast({
        title: triggerReportUpdate
          ? 'Contexte enregistré et mise à jour lancée'
          : 'Contexte enregistré',
        description: triggerReportUpdate
          ? 'Le document de contexte a été mis à jour et une nouvelle version du rapport est en cours de génération.'
          : 'Le document contexte-complementaire.md a été enregistré.',
      });
      onClose();
    } catch {
      toast({
        title: 'Erreur lors de la sauvegarde',
        description: 'Impossible de mettre à jour le document de contexte.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-sovereign-600" />
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Document de contexte complémentaire
              </h2>
              {contextDoc?.updated_at && (
                <p className="text-xs text-slate-500">
                  {contextDoc.filename} — Dernière modification :{' '}
                  {formatDateTime(contextDoc.updated_at)}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600"
            aria-label="Fermer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-5 space-y-3 overflow-y-auto flex-1">
          <p className="text-sm text-slate-600">
            Ce document est conservé avec votre projet et automatiquement transmis à
            l&apos;auditeur IA lors de chaque génération de rapport (avec la version
            précédente du rapport).
          </p>

          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-slate-500">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              Chargement du contexte...
            </div>
          ) : (
            <textarea
              value={markdown}
              onChange={(e) => setMarkdown(e.target.value)}
              rows={14}
              className="input font-mono text-sm w-full min-h-[280px]"
              placeholder="# Contexte complémentaire du projet..."
            />
          )}
        </div>

        <div className="p-5 border-t border-slate-200 flex flex-wrap justify-end gap-3 bg-slate-50">
          <Button type="button" variant="secondary" onClick={onClose}>
            Fermer
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={updateMutation.isPending || isLoading}
            onClick={() => handleSave(false)}
          >
            <Save className="h-4 w-4 mr-2" />
            Enregistrer uniquement
          </Button>
          <Button
            type="button"
            disabled={updateMutation.isPending || isLoading}
            onClick={() => handleSave(true)}
          >
            {updateMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Enregistrer et régénérer le rapport
          </Button>
        </div>
      </div>
    </div>
  );
}
