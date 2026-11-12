'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCorpusArticle } from '@/hooks/useApi';
import { corpusApi, type CorpusArticleItem, type MatchedArticleDetail } from '@/lib/api';
import { JurisdictionBadge, RuleTypeBadge, SanctionBadge } from './corpus-badges';
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  Loader2,
  Scale,
  ShieldAlert,
  Tag,
  Users,
} from 'lucide-react';
import { toast } from '@/hooks/use-toast';

interface ArticleDetailDialogProps {
  articleId: string | null;
  initialArticle?: MatchedArticleDetail | CorpusArticleItem | null;
  onClose: () => void;
  onSelectArticle?: (articleId: string) => void;
}

export function ArticleDetailDialog({
  articleId,
  initialArticle,
  onClose,
  onSelectArticle,
}: ArticleDetailDialogProps) {
  const { data: fetchedArticle, isLoading } = useCorpusArticle(articleId);
  const article = fetchedArticle || initialArticle || null;
  const fullArticle: CorpusArticleItem | null =
    fetchedArticle || (initialArticle && 'text_id' in initialArticle ? (initialArticle as CorpusArticleItem) : null);
  const [downloadingPdf, setDownloadingPdf] = React.useState(false);

  const handleDownloadPdf = async () => {
    if (!fullArticle?.text_id) return;
    setDownloadingPdf(true);
    try {
      const { blob, filename } = await corpusApi.downloadPdf(fullArticle.text_id);
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
        description: 'Le PDF officiel de ce texte n’est pas disponible.',
        variant: 'destructive',
      });
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <Dialog open={!!articleId} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-3xl max-h-[88vh] overflow-y-auto">
        {!article && isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin text-sovereign-600" />
            <span className="text-sm">Chargement du texte officiel de l’article…</span>
          </div>
        ) : article ? (
          <>
            <DialogHeader>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <JurisdictionBadge jurisdiction={article.jurisdiction} />
                <Badge variant="outline" className="text-xs font-mono text-slate-700 bg-slate-50">
                  {article.text_code}
                </Badge>
                <SanctionBadge hasSanction={article.has_sanction} />
                <RuleTypeBadge ruleType={article.compliance_rule_type} />
              </div>
              <DialogTitle className="text-xl text-slate-900 flex items-start gap-2">
                <Scale className="w-5 h-5 text-sovereign-600 shrink-0 mt-1" />
                <span>
                  {article.article_number}
                  {article.title ? ` — ${article.title}` : ''}
                </span>
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-600 space-y-1 pt-1">
                <span className="block font-medium text-slate-700">{article.text_title}</span>
                <span className="block">
                  Autorité : {article.authority}
                  {article.section_breadcrumb ? ` • ${article.section_breadcrumb}` : ''}
                </span>
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              {article.has_sanction && (
                <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2.5">
                  <ShieldAlert className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                  <div className="text-xs text-red-900">
                    <p className="font-semibold">Sanction pénale ou pécuniaire détectée</p>
                    <p className="mt-0.5 text-red-800">
                      {article.sanction_details || 'Cet article prévoit une peine ou sanction en cas de manquement (voir texte officiel ci-dessous).'}
                    </p>
                  </div>
                </div>
              )}

              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5" />
                    Texte intégral officiel (sans altération)
                  </span>
                </div>
                <div className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed font-sans">
                  {article.full_text}
                </div>
              </div>

              {fullArticle && (fullArticle.topics.length > 0 || fullArticle.actors.length > 0) && (
                <div className="grid gap-3 sm:grid-cols-2">
                  {fullArticle.topics.length > 0 && (
                    <div className="p-3 rounded-lg border border-slate-200 bg-white">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
                        <Tag className="w-3 h-3" /> Thématiques
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {fullArticle.topics.map((t) => (
                          <Badge key={t} variant="secondary" className="text-[11px]">{t}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {fullArticle.actors.length > 0 && (
                    <div className="p-3 rounded-lg border border-slate-200 bg-white">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5 flex items-center gap-1">
                        <Users className="w-3 h-3" /> Acteurs visés
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {fullArticle.actors.map((a) => (
                          <Badge key={a} variant="outline" className="text-[11px]">{a}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <DialogFooter className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pt-2 border-t border-slate-100">
              <div className="flex items-center gap-2">
                {onSelectArticle && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!fullArticle?.prev_article_id}
                      onClick={() => fullArticle?.prev_article_id && onSelectArticle(fullArticle.prev_article_id)}
                    >
                      <ChevronLeft className="w-4 h-4 mr-1" />
                      Précédent
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!fullArticle?.next_article_id}
                      onClick={() => fullArticle?.next_article_id && onSelectArticle(fullArticle.next_article_id)}
                    >
                      Suivant
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </Button>
                  </>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {fullArticle?.text_id && (
                  <Button variant="outline" size="sm" onClick={handleDownloadPdf} disabled={downloadingPdf}>
                    {downloadingPdf ? (
                      <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <Download className="w-3.5 h-3.5 mr-1.5" />
                    )}
                    PDF officiel
                  </Button>
                )}
                {article.official_url && (
                  <a
                    href={article.official_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-medium text-sovereign-600 hover:underline px-2"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Source
                  </a>
                )}
                <Button variant="outline" size="sm" asChild>
                  <Link
                    href={
                      fullArticle?.text_id
                        ? `/dashboard/corpus?textId=${fullArticle.text_id}&articleId=${article.id}`
                        : `/dashboard/corpus?articleId=${article.id}`
                    }
                    onClick={onClose}
                  >
                    Ouvrir dans le Code
                  </Link>
                </Button>
                <Button size="sm" onClick={onClose}>Fermer</Button>
              </div>
            </DialogFooter>
          </>
        ) : (
          <div className="py-10 text-center text-sm text-slate-500">
            Article introuvable dans le corpus.
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
