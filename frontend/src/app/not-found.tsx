import Link from 'next/link';
import { Shield, ArrowLeft } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 shadow-sm p-8 text-center space-y-5">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-sovereign-50 text-sovereign-600 mx-auto">
          <Shield className="w-7 h-7" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold uppercase tracking-wider text-sovereign-600">Erreur 404</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Page introuvable</h1>
          <p className="text-sm text-slate-600 mt-2">
            La ressource demandée n&apos;existe pas ou a été déplacée.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Link href="/" className="btn-primary">
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Retour à l&apos;accueil
          </Link>
          <Link href="/dashboard" className="btn-secondary">
            Tableau de bord
          </Link>
        </div>
      </div>
    </div>
  );
}
