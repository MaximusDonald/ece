'use client';

import * as React from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useAdminSources, useAdminExtractedDocuments } from '@/hooks/useApi';
import { adminApi, type LegalDocumentItem } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import {
  FileText,
  Search,
  Download,
  ExternalLink,
  Sparkles,
  ArrowLeft,
  Scale,
  ShieldAlert,
  BookOpen,
  Building,
  Calendar,
  CheckCircle2,
  FileCode,
  Tag,
  Hash,
  Filter,
  Loader2,
  Globe,
} from 'lucide-react';

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
];

const LEVEL_OPTIONS = [
  { value: '', label: 'Tous les niveaux' },
  { value: 'loi', label: 'Loi' },
  { value: 'décret', label: 'Décret' },
  { value: 'règlement', label: 'Règlement' },
  { value: 'directive', label: 'Directive' },
  { value: 'décision', label: 'Décision' },
  { value: 'guide', label: 'Guide / Recommandation' },
];

export default function AdminExtractedDocumentsPage() {
  const searchParams = useSearchParams();
  const initialParentId = searchParams.get('parent_id') || '';

  const { data: parentSources } = useAdminSources();
  const [selectedParentId, setSelectedParentId] = React.useState<string>(initialParentId);
  const [selectedCountry, setSelectedCountry] = React.useState<string>('');
  const [selectedLevel, setSelectedLevel] = React.useState<string>('');
  const [searchTerm, setSearchTerm] = React.useState<string>('');
  const [inspectingDoc, setInspectingDoc] = React.useState<LegalDocumentItem | null>(null);

  const { data: documents, isLoading, refetch } = useAdminExtractedDocuments({
    parent_id: selectedParentId || undefined,
    country_code: selectedCountry || undefined,
    level: selectedLevel || undefined,
    search: searchTerm || undefined,
  });

  const totalSanctionsCount = React.useMemo(() => {
    if (!documents) return 0;
    return documents.reduce((sum, doc) => {
      const sanctionsInDoc = doc.extracted_articles?.filter((a) => a.has_sanction).length || 0;
      return sum + sanctionsInDoc;
    }, 0);
  }, [documents]);

  const totalTermsCount = React.useMemo(() => {
    if (!documents) return 0;
    return documents.reduce((sum, doc) => sum + Object.keys(doc.legal_terms || {}).length, 0);
  }, [documents]);

  const handleDownloadMinioPdf = (docItem: LegalDocumentItem) => {
    const downloadUrl = adminApi.downloadDocumentUrl(docItem.id);
    window.open(downloadUrl, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link
              href="/dashboard/admin/sources"
              className="inline-flex items-center text-xs font-semibold text-sovereign-600 hover:text-sovereign-800 gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Retour aux portails officiels</span>
            </Link>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Bibliothèque juridique extraite par IA
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Textes de lois, décrets et règlements découverts par le crawler, indexés avec leurs fichiers sources PDF d'origine et structurés par l'IA.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/dashboard/admin/sources">
            <Button variant="outline" className="gap-2 border-slate-200 hover:bg-slate-50">
              <Globe className="w-4 h-4 text-slate-600" />
              <span>Gérer les portails racines</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-white border-slate-200 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Lois & Décrets</p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{documents?.length || 0}</h3>
              <p className="text-xs text-slate-400 mt-0.5">Documents juridiques indexés</p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600">
              <BookOpen className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border-slate-200 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Fichiers PDF sources</p>
              <h3 className="text-2xl font-bold text-emerald-700 mt-1">
                {documents?.filter((d) => d.original_filename || d.minio_object_path).length || 0}
              </h3>
              <p className="text-xs text-emerald-600 mt-0.5">Archivés MinIO S3 & téléchargeables</p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
              <Download className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border-slate-200 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Termes Juridiques</p>
              <h3 className="text-2xl font-bold text-purple-700 mt-1">{totalTermsCount}</h3>
              <p className="text-xs text-purple-600 mt-0.5">Définitions légales extraites</p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600">
              <Tag className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border-slate-200 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Régimes de Sanctions</p>
              <h3 className="text-2xl font-bold text-rose-700 mt-1">{totalSanctionsCount}</h3>
              <p className="text-xs text-rose-600 mt-0.5">Articles avec peines/amendes</p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-rose-50 flex items-center justify-center text-rose-600">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Toolbar */}
      <Card className="bg-white border-slate-200 shadow-xs">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Rechercher titre, article, mot-clé..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 text-sm"
              />
            </div>

            <Select value={selectedParentId || 'all'} onValueChange={(val) => setSelectedParentId(val === 'all' ? '' : val)}>
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Tous les portails" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les portails sources</SelectItem>
                {parentSources?.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.title} ({p.authority})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedCountry || 'all'} onValueChange={(val) => setSelectedCountry(val === 'all' ? '' : val)}>
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Toutes les juridictions" />
              </SelectTrigger>
              <SelectContent>
                {COUNTRY_OPTIONS.map((c) => (
                  <SelectItem key={c.value || 'all'} value={c.value || 'all'}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedLevel || 'all'} onValueChange={(val) => setSelectedLevel(val === 'all' ? '' : val)}>
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Tous les niveaux normatifs" />
              </SelectTrigger>
              <SelectContent>
                {LEVEL_OPTIONS.map((l) => (
                  <SelectItem key={l.value || 'all'} value={l.value || 'all'}>
                    {l.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Documents Table */}
      <Card className="bg-white border-slate-200 shadow-xs">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 className="w-8 h-8 text-sovereign-600 animate-spin" />
              <p className="text-sm text-slate-500">Chargement des textes juridiques extraits...</p>
            </div>
          ) : documents && documents.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/70 border-b border-slate-200">
                    <TableHead className="font-semibold text-slate-700">Titre de la loi / Texte</TableHead>
                    <TableHead className="font-semibold text-slate-700">Fichier PDF d'origine</TableHead>
                    <TableHead className="font-semibold text-slate-700">Portail source</TableHead>
                    <TableHead className="font-semibold text-slate-700">Juridiction</TableHead>
                    <TableHead className="font-semibold text-slate-700">Niveau</TableHead>
                    <TableHead className="font-semibold text-slate-700 text-center">Articles IA</TableHead>
                    <TableHead className="text-right font-semibold text-slate-700">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.id} className="hover:bg-slate-50/60 border-b border-slate-100">
                      {/* Document Title */}
                      <TableCell className="py-3.5 max-w-[280px]">
                        <div className="flex items-start gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-700 shrink-0 mt-0.5 border border-emerald-100">
                            <Scale className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <span className="font-semibold text-slate-900 text-sm block truncate">
                              {doc.title}
                            </span>
                            <span className="text-xs text-slate-500 block truncate">
                              {doc.authority || 'Autorité de régulation'}
                            </span>
                          </div>
                        </div>
                      </TableCell>

                      {/* Original PDF Filename (crucial for user) */}
                      <TableCell className="py-3.5 max-w-[200px]">
                        {doc.original_filename ? (
                          <div className="flex items-center gap-1.5 text-xs text-slate-800 font-mono bg-slate-100 px-2 py-1 rounded border border-slate-200 truncate">
                            <FileCode className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                            <span className="truncate" title={doc.original_filename}>
                              {doc.original_filename}
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">Page Web HTML</span>
                        )}
                      </TableCell>

                      {/* Source Parent Portal */}
                      <TableCell className="py-3.5">
                        <span className="text-xs text-slate-700 font-medium block truncate max-w-[160px]">
                          {doc.parent_title || doc.parent_authority || 'Portail racine'}
                        </span>
                      </TableCell>

                      {/* Country */}
                      <TableCell className="py-3.5">
                        {doc.country_code ? (
                          <Badge variant="outline" className="font-mono text-xs font-semibold bg-slate-50 text-slate-700 border-slate-200">
                            {doc.country_code.toUpperCase()}
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="text-xs">
                            Supranational
                          </Badge>
                        )}
                      </TableCell>

                      {/* Normative Level */}
                      <TableCell className="py-3.5">
                        <Badge variant="outline" className="capitalize text-xs text-slate-700 border-slate-200">
                          {doc.level}
                        </Badge>
                      </TableCell>

                      {/* Articles Count */}
                      <TableCell className="py-3.5 text-center">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                          <Hash className="w-3 h-3" />
                          {doc.article_count || 0}
                        </span>
                      </TableCell>

                      {/* Actions */}
                      <TableCell className="py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* AI Inspection Card */}
                          <Button
                            variant="default"
                            size="sm"
                            className="h-8 px-2.5 gap-1.5 bg-sovereign-600 hover:bg-sovereign-700 text-white text-xs font-medium"
                            onClick={() => setInspectingDoc(doc)}
                            title="Ouvrir la fiche d'analyse juridique IA"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Fiche IA</span>
                          </Button>

                          {/* MinIO PDF Download */}
                          {doc.minio_object_path && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-8 px-2 gap-1 text-slate-700 border-slate-200 hover:bg-slate-50 text-xs"
                              onClick={() => handleDownloadMinioPdf(doc)}
                              title="Télécharger le PDF original archivé dans MinIO"
                            >
                              <Download className="w-3.5 h-3.5 text-emerald-600" />
                              <span className="hidden lg:inline">PDF</span>
                            </Button>
                          )}

                          {/* Direct Source Link */}
                          {doc.download_url && (
                            <a
                              href={doc.download_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center justify-center h-8 w-8 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                              title="Ouvrir le lien source original de téléchargement"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-16 px-4">
              <BookOpen className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-900">Aucun document juridique trouvé</h3>
              <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
                Aucun texte ou loi ne correspond à vos filtres. Lancez une collecte IA depuis la page des portails officiels pour enrichir automatiquement cette bibliothèque.
              </p>
              <div className="mt-4">
                <Link href="/dashboard/admin/sources">
                  <Button className="bg-sovereign-600 hover:bg-sovereign-700 text-white gap-2">
                    <Globe className="w-4 h-4" />
                    <span>Aller aux portails officiels</span>
                  </Button>
                </Link>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal: AI Legal Analysis Breakdown */}
      <Dialog open={Boolean(inspectingDoc)} onOpenChange={(open) => !open && setInspectingDoc(null)}>
        <DialogContent className="max-w-3xl max-h-[88vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200 uppercase font-mono">
                {inspectingDoc?.level} • {inspectingDoc?.country_code || 'Supranational'}
              </Badge>
              {inspectingDoc?.original_filename && (
                <span className="text-xs text-slate-500 font-mono truncate max-w-sm">
                  {inspectingDoc.original_filename}
                </span>
              )}
            </div>
            <DialogTitle className="text-lg font-bold text-slate-900">
              {inspectingDoc?.title}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              Portail parent : {inspectingDoc?.parent_title || inspectingDoc?.parent_authority || 'N/A'} • Enregistré le {inspectingDoc ? formatDateTime(inspectingDoc.created_at) : ''}
            </DialogDescription>
          </DialogHeader>

          {inspectingDoc && (
            <div className="space-y-5 py-2">
              {/* Executive Summary */}
              {inspectingDoc.summary && (
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-sovereign-600" />
                    Synthèse Juridique IA
                  </h4>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {inspectingDoc.summary}
                  </p>
                </div>
              )}

              {/* Legal Terms Glossary */}
              {inspectingDoc.legal_terms && Object.keys(inspectingDoc.legal_terms).length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <Tag className="w-3.5 h-3.5 text-purple-600" />
                    Glossaire des Définitions Juridiques Extraites
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {Object.entries(inspectingDoc.legal_terms).map(([term, def]) => (
                      <div key={term} className="p-2.5 rounded-lg border border-slate-200 bg-white shadow-2xs">
                        <span className="text-xs font-bold text-purple-900 block capitalize">{term}</span>
                        <span className="text-[11px] text-slate-600 mt-0.5 block leading-normal">
                          {typeof def === 'string' ? def : JSON.stringify(def)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Extracted Articles with Sanctions */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <Scale className="w-3.5 h-3.5 text-blue-600" />
                    Articles Clés & Sanctions Identifiés ({inspectingDoc.extracted_articles?.length || 0})
                  </h4>
                </div>

                {inspectingDoc.extracted_articles && inspectingDoc.extracted_articles.length > 0 ? (
                  <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
                    {inspectingDoc.extracted_articles.map((art, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg border ${
                          art.has_sanction
                            ? 'bg-rose-50/40 border-rose-200'
                            : 'bg-white border-slate-200'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-bold text-slate-900 font-mono">
                            {art.article_ref || `Article ${idx + 1}`}
                          </span>
                          {art.has_sanction && (
                            <Badge variant="outline" className="bg-rose-100 text-rose-800 border-rose-300 text-[10px] font-semibold gap-1">
                              <ShieldAlert className="w-3 h-3 text-rose-600" />
                              Sanction / Pénalité
                            </Badge>
                          )}
                        </div>
                        {art.title && (
                          <p className="text-xs font-medium text-slate-800 mt-1">{art.title}</p>
                        )}
                        {art.content_summary && (
                          <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                            {art.content_summary}
                          </p>
                        )}
                        {art.has_sanction && art.sanction_details && (
                          <div className="mt-2 text-xs font-medium text-rose-800 bg-rose-100/70 p-2 rounded border border-rose-200">
                            <strong>Sanction applicable :</strong> {art.sanction_details}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">Aucun article n'a été découpé spécifiquement pour ce document.</p>
                )}
              </div>
            </div>
          )}

          <DialogFooter className="pt-2 flex items-center justify-between sm:justify-between">
            {inspectingDoc?.minio_object_path ? (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50"
                onClick={() => inspectingDoc && handleDownloadMinioPdf(inspectingDoc)}
              >
                <Download className="w-3.5 h-3.5" />
                <span>Télécharger le PDF original (MinIO)</span>
              </Button>
            ) : <div />}

            <Button variant="outline" onClick={() => setInspectingDoc(null)}>
              Fermer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
