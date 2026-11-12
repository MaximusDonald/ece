'use client';

import * as React from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  useCorpusSummary,
  useCorpusTexts,
  useCorpusSections,
  useCorpusArticles,
} from '@/hooks/useApi';
import { corpusApi, type CorpusArticleItem, type LegalTextItem } from '@/lib/api';
import { ArticleDetailDialog } from './ArticleDetailDialog';
import { JurisdictionBadge, RuleTypeBadge, SanctionBadge } from './corpus-badges';
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Download,
  FolderTree,
  Layers,
  Loader2,
  Scale,
  Search,
  ShieldAlert,
  Sparkles,
  X,
} from 'lucide-react';
import { toast } from '@/hooks/use-toast';

const PAGE_SIZE = 25;

const RULE_TYPE_FILTERS = [
  { value: 'all', label: 'Toutes natures de règles' },
  { value: 'mandatory', label: 'Obligation impérative' },
  { value: 'prohibition', label: 'Interdiction' },
  { value: 'conditional', label: 'Condition / Autorisation' },
  { value: 'sanction', label: 'Sanction pénale / pécuniaire' },
  { value: 'recommendation', label: 'Recommandation' },
  { value: 'definition', label: 'Définition' },
];

export function CorpusExplorerView({ adminContext = false }: { adminContext?: boolean }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const basePath = adminContext ? '/dashboard/admin/corpus' : '/dashboard/corpus';

  const [selectedTextId, setSelectedTextId] = React.useState<string>(searchParams.get('textId') || '');
  const [selectedSectionId, setSelectedSectionId] = React.useState<string>('');
  const [selectedJurisdiction, setSelectedJurisdiction] = React.useState<string>('all');
  const [selectedRuleType, setSelectedRuleType] = React.useState<string>('all');
  const [onlySanctions, setOnlySanctions] = React.useState<boolean>(false);
  const [searchInput, setSearchInput] = React.useState<string>('');
  const [debouncedQuery, setDebouncedQuery] = React.useState<string>('');
  const [searchMode, setSearchMode] = React.useState<'keyword' | 'hybrid'>('keyword');
  const [page, setPage] = React.useState<number>(0);

  const [activeArticleId, setActiveArticleId] = React.useState<string | null>(
    searchParams.get('articleId') || null
  );
  const [activeInitialArticle, setActiveInitialArticle] = React.useState<CorpusArticleItem | null>(null);
  const [downloadingTextId, setDownloadingTextId] = React.useState<string | null>(null);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchInput.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  React.useEffect(() => {
    const t = searchParams.get('textId') || '';
    const a = searchParams.get('articleId') || null;
    if (t) setSelectedTextId(t);
    if (a) setActiveArticleId(a);
  }, [searchParams]);

  const { data: summary } = useCorpusSummary();
  const { data: texts, isLoading: loadingTexts } = useCorpusTexts(
    selectedJurisdiction !== 'all' ? selectedJurisdiction : undefined
  );
  const { data: sections, isLoading: loadingSections } = useCorpusSections(selectedTextId || undefined);

  const activeText: LegalTextItem | undefined = React.useMemo(
    () => texts?.find((t) => t.id === selectedTextId),
    [texts, selectedTextId]
  );

  const effectiveMode: 'keyword' | 'hybrid' = debouncedQuery ? searchMode : 'keyword';

  const { data: articlesPage, isLoading: loadingArticles, isFetching } = useCorpusArticles({
    text_id: selectedTextId || undefined,
    section_id: effectiveMode === 'keyword' && selectedSectionId ? selectedSectionId : undefined,
    jurisdiction: selectedJurisdiction !== 'all' ? selectedJurisdiction : undefined,
    has_sanction: onlySanctions ? true : undefined,
    compliance_rule_type: selectedRuleType !== 'all' ? selectedRuleType : undefined,
    q: debouncedQuery || undefined,
    mode: effectiveMode,
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  });

  const handleSelectText = (textId: string) => {
    const next = selectedTextId === textId ? '' : textId;
    setSelectedTextId(next);
    setSelectedSectionId('');
    setPage(0);
    const params = new URLSearchParams(searchParams.toString());
    if (next) params.set('textId', next);
    else params.delete('textId');
    params.delete('articleId');
    const qs = params.toString();
    router.replace(`${basePath}${qs ? `?${qs}` : ''}`, { scroll: false });
  };

  const handleSelectSection = (sectionId: string) => {
    setSelectedSectionId((prev) => (prev === sectionId ? '' : sectionId));
    setPage(0);
  };

  const handleDownloadPdf = async (textItem: LegalTextItem) => {
    setDownloadingTextId(textItem.id);
    try {
      const { blob, filename } = await corpusApi.downloadPdf(textItem.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast({
        title: 'Téléchargement impossible',
        description: `Le fichier PDF officiel de ${textItem.code} n'est pas disponible.`,
        variant: 'destructive',
      });
    } finally {
      setDownloadingTextId(null);
    }
  };

  const totalArticles = articlesPage?.total || 0;
  const totalPages = Math.max(1, Math.ceil(totalArticles / PAGE_SIZE));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2.5">
            <Scale className="w-6 h-6 text-sovereign-600" />
            <span>Bibliothèque des Codes & Articles de Loi</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Corpus juridique hiérarchisé (Texte → Division → Article intégral sans altération) pour le Bénin, la CEDEAO, l’UEMOA, l’OHADA, l’OAPI et l’Union Africaine.
          </p>
        </div>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-white border-slate-200">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Textes Piliers</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{summary?.total_texts ?? '—'}</p>
            </div>
            <BookOpen className="w-6 h-6 text-sovereign-600 opacity-80" />
          </CardContent>
        </Card>
        <Card className="bg-white border-slate-200">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Divisions / Titres</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{summary?.total_sections ?? '—'}</p>
            </div>
            <FolderTree className="w-6 h-6 text-indigo-600 opacity-80" />
          </CardContent>
        </Card>
        <Card className="bg-white border-slate-200">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Articles indexés</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{summary?.total_articles ?? '—'}</p>
            </div>
            <Layers className="w-6 h-6 text-emerald-600 opacity-80" />
          </CardContent>
        </Card>
        <Card className="bg-white border-slate-200">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Avec sanctions</p>
              <p className="text-2xl font-bold text-red-700 mt-1">{summary?.sanctioned_articles ?? '—'}</p>
            </div>
            <ShieldAlert className="w-6 h-6 text-red-600 opacity-80" />
          </CardContent>
        </Card>
      </div>

      {/* Search & Filter Toolbar */}
      <Card className="bg-white border-slate-200">
        <CardContent className="p-4 space-y-3">
          <div className="flex flex-col lg:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <Input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder={
                  searchMode === 'hybrid'
                    ? 'Recherche sémantique IA (ex: transfert données santé vers cloud étranger)…'
                    : 'Rechercher par numéro (Article 391), mot-clé (DPO, consentement, amende)…'
                }
                className="pl-9 pr-8"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={() => setSearchInput('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  aria-label="Effacer la recherche"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 shrink-0">
              <button
                type="button"
                onClick={() => { setSearchMode('keyword'); setPage(0); }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  searchMode === 'keyword'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Mot-clé exact
              </button>
              <button
                type="button"
                onClick={() => { setSearchMode('hybrid'); setPage(0); }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium inline-flex items-center gap-1 transition-colors ${
                  searchMode === 'hybrid'
                    ? 'bg-sovereign-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                Hybride IA (RAG)
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Select
              value={selectedJurisdiction}
              onValueChange={(v) => {
                setSelectedJurisdiction(v);
                setSelectedTextId('');
                setSelectedSectionId('');
                setPage(0);
              }}
            >
              <SelectTrigger className="w-[180px] h-9 text-xs">
                <SelectValue placeholder="Juridiction" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes juridictions</SelectItem>
                {(summary?.jurisdictions || ['BJ', 'CEDEAO', 'OAPI', 'OHADA', 'UA', 'UEMOA']).map((j) => (
                  <SelectItem key={j} value={j}>{j}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={selectedRuleType}
              onValueChange={(v) => {
                setSelectedRuleType(v);
                setPage(0);
              }}
            >
              <SelectTrigger className="w-[220px] h-9 text-xs">
                <SelectValue placeholder="Nature de règle" />
              </SelectTrigger>
              <SelectContent>
                {RULE_TYPE_FILTERS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              type="button"
              variant={onlySanctions ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setOnlySanctions((prev) => !prev);
                setPage(0);
              }}
              className={onlySanctions ? 'bg-red-600 hover:bg-red-700 text-white' : 'text-red-700 border-red-200 hover:bg-red-50'}
            >
              <ShieldAlert className="w-3.5 h-3.5 mr-1.5" />
              Sanctions uniquement
            </Button>

            {(selectedTextId || selectedSectionId || selectedJurisdiction !== 'all' || onlySanctions || selectedRuleType !== 'all' || debouncedQuery) && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSelectedTextId('');
                  setSelectedSectionId('');
                  setSelectedJurisdiction('all');
                  setSelectedRuleType('all');
                  setOnlySanctions(false);
                  setSearchInput('');
                  setPage(0);
                }}
              >
                Réinitialiser les filtres
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Split Explorer: Left TOC + Center Articles */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Sidebar: Master Texts & Hierarchical Sections */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="border-slate-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-slate-900">
                1. Textes Piliers ({texts?.length || 0})
              </CardTitle>
              <CardDescription className="text-xs">
                Sélectionnez un code ou règlement pour afficher son sommaire hiérarchique.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0 space-y-1.5 max-h-[380px] overflow-y-auto">
              {loadingTexts ? (
                <div className="py-6 flex justify-center">
                  <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
                </div>
              ) : (
                texts?.map((t) => {
                  const isSelected = t.id === selectedTextId;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => handleSelectText(t.id)}
                      className={`w-full text-left p-2.5 rounded-lg border transition-colors ${
                        isSelected
                          ? 'bg-sovereign-50 border-sovereign-300 text-sovereign-950'
                          : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-800'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <div className="flex items-center gap-1.5">
                          <JurisdictionBadge jurisdiction={t.jurisdiction} />
                          <span className="text-xs font-mono font-semibold">{t.code}</span>
                        </div>
                        <span className="text-[11px] font-medium text-slate-500">
                          {t.total_articles} art.
                        </span>
                      </div>
                      <p className="text-xs font-medium line-clamp-2">{t.title}</p>
                    </button>
                  );
                })
              )}
            </CardContent>
          </Card>

          {selectedTextId && (
            <Card className="border-slate-200">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-sm font-semibold text-slate-900">
                    2. Sommaire ({activeText?.code})
                  </CardTitle>
                  {activeText?.pdf_path && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => handleDownloadPdf(activeText)}
                      disabled={downloadingTextId === activeText.id}
                    >
                      {downloadingTextId === activeText.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Download className="w-3 h-3 mr-1" />
                      )}
                      PDF
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="pt-1 space-y-1 max-h-[460px] overflow-y-auto">
                <button
                  type="button"
                  onClick={() => { setSelectedSectionId(''); setPage(0); }}
                  className={`w-full text-left px-2.5 py-1.5 rounded text-xs font-medium ${
                    !selectedSectionId
                      ? 'bg-sovereign-600 text-white'
                      : 'text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  Tout le texte ({activeText?.total_articles ?? 0} articles)
                </button>

                {loadingSections ? (
                  <div className="py-4 flex justify-center">
                    <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                  </div>
                ) : sections && sections.length > 0 ? (
                  sections.map((sec) => {
                    const depth = Math.min(3, Math.max(0, sec.breadcrumb.split(' > ').length - 1));
                    const isSecSelected = selectedSectionId === sec.id;
                    return (
                      <button
                        key={sec.id}
                        type="button"
                        onClick={() => handleSelectSection(sec.id)}
                        style={{ paddingLeft: `${10 + depth * 12}px` }}
                        className={`w-full text-left pr-2 py-1.5 rounded text-xs transition-colors flex items-center justify-between gap-2 ${
                          isSecSelected
                            ? 'bg-sovereign-100 text-sovereign-900 font-semibold'
                            : 'text-slate-700 hover:bg-slate-100'
                        }`}
                      >
                        <span className="truncate">
                          <span className="font-medium">{sec.level_name}</span>
                          {sec.title && sec.title !== sec.level_name ? ` — ${sec.title}` : ''}
                        </span>
                        <span className="text-[10px] text-slate-400 shrink-0">{sec.article_count}</span>
                      </button>
                    );
                  })
                ) : (
                  <p className="text-xs text-slate-400 px-2 py-2">Aucune division détectée.</p>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right / Center Pane: Article Cards */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-600 px-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900">{totalArticles}</span>
              <span>article(s) trouvé(s)</span>
              {effectiveMode === 'hybrid' && (
                <Badge variant="outline" className="text-[10px] bg-sovereign-50 text-sovereign-700 border-sovereign-200">
                  Classement Hybride Vectoriel + BM25
                </Badge>
              )}
              {isFetching && <Loader2 className="w-3.5 h-3.5 animate-spin text-sovereign-600" />}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </Button>
                <span className="px-2">
                  Page {page + 1} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2"
                  disabled={page + 1 >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            )}
          </div>

          {loadingArticles ? (
            <Card className="border-slate-200">
              <CardContent className="py-16 flex flex-col items-center justify-center gap-2 text-slate-500">
                <Loader2 className="w-6 h-6 animate-spin text-sovereign-600" />
                <span className="text-sm">Chargement des articles officiels…</span>
              </CardContent>
            </Card>
          ) : articlesPage && articlesPage.items.length > 0 ? (
            <div className="space-y-3">
              {articlesPage.items.map((art) => (
                <Card
                  key={art.id}
                  onClick={() => {
                    setActiveInitialArticle(art);
                    setActiveArticleId(art.id);
                  }}
                  className="border-slate-200 hover:border-sovereign-300 hover:shadow-xs transition-all cursor-pointer bg-white"
                >
                  <CardContent className="p-4 space-y-2.5">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <JurisdictionBadge jurisdiction={art.jurisdiction} />
                        <Badge variant="outline" className="text-[11px] font-mono bg-slate-50 text-slate-700">
                          {art.text_code}
                        </Badge>
                        <SanctionBadge hasSanction={art.has_sanction} />
                        <RuleTypeBadge ruleType={art.compliance_rule_type} />
                        {typeof art.score === 'number' && (
                          <Badge variant="outline" className="text-[10px] font-mono bg-emerald-50 text-emerald-700 border-emerald-200">
                            Score {(art.score * 100).toFixed(0)}%
                          </Badge>
                        )}
                      </div>
                      <span className="text-xs font-medium text-sovereign-600 hover:underline shrink-0">
                        Consulter la fiche →
                      </span>
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-slate-900">
                        {art.article_number}
                        {art.title ? ` — ${art.title}` : ''}
                      </h3>
                      {art.section_breadcrumb && (
                        <p className="text-[11px] text-slate-500 mt-0.5">{art.section_breadcrumb}</p>
                      )}
                    </div>

                    <p className="text-xs text-slate-700 line-clamp-3 leading-relaxed">
                      {art.full_text}
                    </p>

                    {art.has_sanction && art.sanction_details && (
                      <div className="text-[11px] text-red-800 bg-red-50/80 border border-red-200 rounded px-2.5 py-1.5 flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5 text-red-600 shrink-0" />
                        <span className="truncate">{art.sanction_details}</span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="border-slate-200">
              <CardContent className="py-12 text-center text-sm text-slate-500">
                Aucun article ne correspond aux filtres sélectionnés.
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Article Detail Modal */}
      <ArticleDetailDialog
        articleId={activeArticleId}
        initialArticle={activeInitialArticle}
        onClose={() => {
          setActiveArticleId(null);
          setActiveInitialArticle(null);
        }}
        onSelectArticle={(nextId) => {
          setActiveInitialArticle(null);
          setActiveArticleId(nextId);
        }}
      />
    </div>
  );
}
