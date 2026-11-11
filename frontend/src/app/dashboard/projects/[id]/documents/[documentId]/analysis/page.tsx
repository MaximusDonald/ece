'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useDocumentAnalysis, useDocumentExtraction, useDocumentPipeline } from '@/hooks/useApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ChevronLeft, Brain, AlertTriangle, Search } from 'lucide-react';
import { formatDateTime, getApiErrorMessage } from '@/lib/utils';

const SUGGESTED_FIELD_LABELS: Record<string, string> = {
  base_legale_traitement: 'base légale du traitement',
  droits_personnes_concernees: 'droits des personnes concernées',
  localisation_stockage_donnees: 'lieu de stockage des données',
  mesures_securite_transfert: 'mesures de sécurité des transferts',
  conformite_rgpd_ou_loi_beninoise: 'règles de protection des données applicables',
  localisation_hebergement: 'lieu d’hébergement des données',
  hosting_location: 'lieu d’hébergement des données',
  sous_traitant: 'sous-traitants concernés',
  subcontractor: 'sous-traitants concernés',
};

function findSourceContext(markdown: string | undefined, reference: string) {
  if (!markdown || !reference) return null;

  const escapedReference = reference.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  let match = new RegExp(escapedReference, 'i').exec(markdown);
  const sectionNumber = reference.match(/\d+(?:\.\d+)+/)?.[0];
  if (!match && sectionNumber) {
    const escapedNumber = sectionNumber.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    match = new RegExp(`^\\s*(?:#{1,6}\\s*)?(?:section\\s+)?${escapedNumber}\\b.*$`, 'im').exec(markdown);
  }
  if (!match) return null;

  let page: string | undefined;
  const pageHeadings = markdown.slice(0, match.index).matchAll(/^\s*#{1,6}\s*Page\s+(\d+)\s*$/gim);
  for (const heading of pageHeadings) page = heading[1];
  const excerpt = markdown.slice(match.index, match.index + 260).replace(/\s+/g, ' ').trim();
  return { page, excerpt };
}

function readableZoneDescription(description: string) {
  if (description.startsWith('Clause data_protection')) {
    return 'La clause de protection des données personnelles reste trop générale.';
  }
  if (description.startsWith('Clause payment_services')) {
    return 'La clause sur les services de paiement reste trop générale.';
  }
  return description;
}

export default function AnalysisPage() {
  const params = useParams();
  const projectId = params.id as string;
  const documentId = params.documentId as string;
  const { data: analysis, isLoading, error, refetch } = useDocumentAnalysis(projectId, documentId);
  const { data: extraction } = useDocumentExtraction(projectId, documentId);
  const { data: pipeline } = useDocumentPipeline(projectId, documentId);
  const legalStep = pipeline?.steps.find((step) => step.key === 'legal_research');
  const apiError = error as { response?: { status?: number; data?: { detail?: string } } } | null;
  const isAnalysisPending = apiError?.response?.status === 404 &&
    ['Extraction not found', 'Analysis not found'].includes(apiError.response.data?.detail || '');

  if (isLoading || (!analysis && isAnalysisPending)) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-12" role="status" aria-live="polite">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
        <p className="font-medium text-slate-700">Analyses en cours</p>
        <p className="text-sm text-slate-500">Les résultats apparaîtront ici dès que le traitement sera terminé.</p>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="text-center py-12">
        <Brain className="h-12 w-12 text-danger-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-900 mb-2">Impossible de charger l’analyse</h3>
        <p role="alert" className="text-slate-500 mb-4">{getApiErrorMessage(error, 'Une erreur est survenue lors du chargement.')}</p>
        <Button variant="secondary" onClick={() => void refetch()} className="mb-3">Réessayer</Button>
        <br />
        <Link href={`/dashboard/projects/${projectId}`}>
          <Button variant="secondary">Retour au projet</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link href={`/dashboard/projects/${projectId}`} className="text-sm text-slate-500 hover:underline flex items-center gap-1">
            <ChevronLeft className="h-4 w-4" />
            Projet
          </Link>
          <div>
            <h1 className="page-title">Analyse sémantique</h1>
            <p className="page-subtitle">Entités détectées, zones floues et classification des clauses</p>
          </div>
        </div>
      </div>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Métadonnées de l'analyse</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="p-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-slate-500">Date d'analyse</p>
            <p className="font-medium">{formatDateTime(analysis.created_at)}</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-slate-500">Entités totales</p>
            <p className="text-2xl font-bold text-slate-900">
              {Object.values(analysis.entities).flat().length}
            </p>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg">
            <p className="text-sm text-slate-500">Zones floues détectées</p>
            <p className="text-2xl font-bold text-slate-900">{analysis.vague_zones.length}</p>
          </div>
        </CardContent>
      </Card>

      {/* Entities */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Entités nommées détectées</CardTitle>
          <Badge variant="outline">{Object.values(analysis.entities).flat().length} total</Badge>
        </CardHeader>
        <CardContent>
          {Object.entries(analysis.entities).map(([type, entities]) => (
            entities && entities.length > 0 && (
              <div key={type} className="mb-6">
                <h4 className="font-medium text-slate-900 mb-3 capitalize">{type.replace('_', ' ')}</h4>
                <div className="flex flex-wrap gap-2">
                  {entities.map((entity: string, i: number) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {entity}
                    </Badge>
                  ))}
                </div>
              </div>
            )
          ))}
          {Object.values(analysis.entities).flat().length === 0 && (
            <p className="text-slate-500 text-center py-4">Aucune entité détectée</p>
          )}
        </CardContent>
      </Card>

      {/* Vague Zones */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Zones floues nécessitant des précisions</CardTitle>
          <Badge variant={analysis.vague_zones.length > 0 ? 'warning' : 'conforme'}>
            {analysis.vague_zones.length} détectée(s)
          </Badge>
        </CardHeader>
        <CardContent>
          {analysis.vague_zones.length > 0 ? (
            <div className="space-y-4">
              {analysis.vague_zones.map((zone, index) => (
                <div key={index} className="p-4 bg-warning-50 border border-warning-200 rounded-lg">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4 text-warning-600" />
                        <span className="font-medium text-warning-800">Repère proposé : {zone.clause_ref}</span>
                      </div>
                      <p className="text-slate-700 mb-2 whitespace-pre-line">{readableZoneDescription(zone.description)}</p>
                      {!zone.description.includes('Extrait exact') && !zone.description.includes('Passage autour') && (
                        <div className="mb-3 rounded-md border border-amber-200 bg-white/70 p-3 text-sm text-slate-700">
                          {(() => {
                            const context = findSourceContext(extraction?.markdown, zone.clause_ref);
                            if (!context) {
                              return <p>Repère proposé par l’analyse. Il n’a pas pu être retrouvé automatiquement dans le texte extrait.</p>;
                            }
                            return (
                              <>
                                {context.page && <p className="mb-1 font-medium">Page {context.page}</p>}
                                <p><span className="font-medium">Passage autour du repère :</span> “{context.excerpt}”</p>
                              </>
                            );
                          })()}
                        </div>
                      )}
                      {zone.suggested_fields && zone.suggested_fields.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {zone.suggested_fields.map((field: string, i: number) => (
                            <Badge key={i} variant="outline" className="text-xs">
                              {SUGGESTED_FIELD_LABELS[field] || field.replaceAll('_', ' ')}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                    <Badge variant="warning">Action requise</Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Search className="h-12 w-12 text-success-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-success-600 mb-2">Aucune zone floue</h3>
              <p className="text-slate-500">Le document est suffisamment précis pour l'analyse juridique.</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-sovereign-200 bg-sovereign-50">
        <CardContent className="p-6">
          <div className="flex items-center gap-3">
            <Brain className="h-8 w-8 text-sovereign-500" />
            <div>
              <h3 className="font-semibold text-sovereign-800">
                {pipeline?.status === 'completed'
                  ? 'Analyse juridique terminée'
                  : legalStep?.status === 'failed'
                    ? 'La recherche juridique a échoué'
                    : legalStep?.status === 'completed'
                      ? 'Recherche juridique terminée'
                      : legalStep?.status === 'retrying'
                        ? 'Nouvelle tentative de recherche juridique'
                        : legalStep?.status === 'running'
                          ? 'Recherche juridique en cours'
                          : 'Recherche juridique en attente'}
              </h3>
              <p className="text-sovereign-600 text-sm">
                {legalStep?.message || 'Vérification du lancement de la recherche juridique…'}
                {pipeline?.error ? ` ${pipeline.error}` : ''}
              </p>
            </div>
          </div>
          <Button asChild variant="outline" className="mt-4">
            <Link href={`/dashboard/projects/${projectId}/documents/${documentId}/pipeline`}>
              {legalStep?.status === 'failed' ? 'Voir l’erreur et relancer' : 'Suivre les étapes de l’audit'}
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button variant="secondary" asChild>
          <Link href={`/dashboard/projects/${projectId}`}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            Retour au projet
          </Link>
        </Button>
      </div>
    </div>
  );
}
