'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Cookies from 'js-cookie';
import { useMe } from '@/hooks/useApi';
import { Shield, ArrowRight, Scale, FileCheck2, Lock, CheckCircle2 } from 'lucide-react';

export default function HomePage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [hasSessionToken, setHasSessionToken] = useState(false);

  useEffect(() => {
    setMounted(true);
    setHasSessionToken(Boolean(Cookies.get('access_token') || Cookies.get('refresh_token')));
  }, []);

  const { data: user, isLoading } = useMe({ enabled: mounted && hasSessionToken });

  useEffect(() => {
    if (mounted && hasSessionToken && !isLoading && user) {
      const isPlatformAdmin = user.is_superuser || user.role === 'platform_admin';
      router.replace(isPlatformAdmin ? '/dashboard/admin/corpus' : '/dashboard');
    }
  }, [mounted, hasSessionToken, isLoading, user, router]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-lg bg-sovereign-500 text-white flex items-center justify-center">
              <Shield className="w-5 h-5" aria-hidden="true" />
            </span>
            <span className="font-bold text-lg text-slate-900">ECO-Compliance Engine</span>
          </Link>
          <Link
            href="/auth/login"
            className="text-sm font-medium text-slate-700 hover:text-sovereign-600 transition-colors"
          >
            Se connecter
          </Link>
        </div>
      </header>

      {/* Hero with a single clear primary CTA */}
      <main className="flex-1">
        <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <span className="inline-flex items-center rounded-full bg-sovereign-50 border border-sovereign-200 px-3.5 py-1 text-xs font-semibold text-sovereign-700">
              Conformité juridique souveraine · CEDEAO · UEMOA · OHADA · OAPI
            </span>
            <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-slate-900 leading-tight">
              Auditez vos dossiers juridiques et techniques en toute traçabilité
            </h1>
            <p className="text-base sm:text-lg text-slate-700 leading-relaxed">
              Déposez vos cahiers des charges, politiques de confidentialité et contrats. ECO-Compliance Engine croise l&apos;ensemble du dossier avec les textes officiels en vigueur, calcule un score stabilisé par domaine et produit un rapport PDF opposable.
            </p>
            <div className="pt-2 flex flex-col items-center gap-3">
              <Link
                href="/auth/register"
                className="btn-primary px-7 py-3.5 text-base shadow-sm"
              >
                Lancer un audit de conformité
                <ArrowRight className="w-5 h-5" aria-hidden="true" />
              </Link>
              <p className="text-xs text-slate-600">
                Déjà inscrit ?{' '}
                <Link href="/auth/login" className="font-medium text-sovereign-600 hover:underline">
                  Accéder à mon espace
                </Link>
              </p>
            </div>
          </div>

          {/* 4 pillars */}
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4 mt-14">
            <div className="card p-5 space-y-2">
              <Scale className="w-6 h-6 text-sovereign-600" aria-hidden="true" />
              <h2 className="font-semibold text-slate-900">Corpus officiel filtré</h2>
              <p className="text-sm text-slate-600">
                Article-RAG hybride limité aux textes en vigueur avec priorité aux normes communautaires et alerte en cas de conflit.
              </p>
            </div>
            <div className="card p-5 space-y-2">
              <FileCheck2 className="w-6 h-6 text-sovereign-600" aria-hidden="true" />
              <h2 className="font-semibold text-slate-900">Analyse multi-documents</h2>
              <p className="text-sm text-slate-600">
                Détection des mesures compensatoires entre vos pièces et préservation des clauses critiques dans les longs contrats.
              </p>
            </div>
            <div className="card p-5 space-y-2">
              <CheckCircle2 className="w-6 h-6 text-sovereign-600" aria-hidden="true" />
              <h2 className="font-semibold text-slate-900">Score stable &amp; explicable</h2>
              <p className="text-sm text-slate-600">
                Rendements décroissants sur 4 facettes juridiques, sanctions dédupliquées par article unique et plancher de précaution.
              </p>
            </div>
            <div className="card p-5 space-y-2">
              <Lock className="w-6 h-6 text-sovereign-600" aria-hidden="true" />
              <h2 className="font-semibold text-slate-900">Piste d&apos;audit juridique</h2>
              <p className="text-sm text-slate-600">
                Qualification de chaque constat, validation humaine horodatée et verrouillage inter-versions pour un rapport PDF unifié.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600">
          <p>ECO-Compliance Engine — Plateforme souveraine d&apos;audit documentaire</p>
          <div className="flex items-center gap-5">
            <Link href="/terms" className="hover:text-sovereign-600 hover:underline">
              Conditions Générales d&apos;Utilisation
            </Link>
            <Link href="/privacy" className="hover:text-sovereign-600 hover:underline">
              Politique de confidentialité
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
