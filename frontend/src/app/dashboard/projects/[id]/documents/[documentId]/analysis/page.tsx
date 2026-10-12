'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useDocumentAnalysis } from '@/hooks/useApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { ChevronLeft, Brain, Tag, AlertTriangle, Search } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';

export default function AnalysisPage() {
  const params = useParams();
  const projectId = params.id as string;
  const documentId = params.documentId as string;
  const { data: analysis, isLoading } = useDocumentAnalysis(projectId, documentId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sovereign-500" />
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="text-center py-12">
        <Brain className="h-12 w-12 text-slate-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-900 mb-2">Analyse non disponible</h3>
        <p className="text-slate-500 mb-4">L'analyse sémantique n'a pas encore été effectuée ou a échoué.</p>
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
                        <span className="font-medium text-warning-800">{zone.clause_ref}</span>
                      </div>
                      <p className="text-slate-700 mb-2">{zone.description}</p>
                      {zone.suggested_fields && zone.suggested_fields.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {zone.suggested_fields.map((field: string, i: number) => (
                            <Badge key={i} variant="outline" className="text-xs">
                              {field.replace('_', ' ')}
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

      {/* Next Steps */}
      <Card className="border-sovereign-200 bg-sovereign-50">
        <CardContent className="p-6">
          <div className="flex items-center gap-3">
            <Brain className="h-8 w-8 text-sovereign-500" />
            <div>
              <h3 className="font-semibold text-sovereign-800">Prochaine étape</h3>
              <p className="text-sovereign-600 text-sm">
                L'analyse sémantique est terminée. Le système va maintenant lancer la recherche juridique 
                (RAG) sur le corpus CEDEAO/UEMOA/OHADA + Bénin pour identifier les obligations applicables.
              </p>
            </div>
          </div>
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