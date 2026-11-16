import type { Metadata } from 'next';
import Link from 'next/link';
import { Shield, ArrowLeft } from 'lucide-react';

export const metadata: Metadata = {
  title: "Conditions Générales d'Utilisation",
  description:
    "Conditions Générales d'Utilisation de la plateforme ECO-Compliance Engine.",
};

export default function TermsOfUsePage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-slate-900">
            <span className="w-8 h-8 rounded-lg bg-sovereign-500 text-white flex items-center justify-center">
              <Shield className="w-4 h-4" aria-hidden="true" />
            </span>
            ECO-Compliance Engine
          </Link>
          <Link href="/" className="text-sm font-medium text-sovereign-600 hover:underline inline-flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Accueil
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <article className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-10 space-y-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-sovereign-600">
              Cadre contractuel
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">
              Conditions Générales d&apos;Utilisation (CGU)
            </h1>
            <p className="text-sm text-slate-600 mt-2">
              Dernière mise à jour : 14 novembre 2026
            </p>
          </div>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-900">1. Objet du service</h2>
            <p className="text-sm leading-relaxed text-slate-700">
              ECO-Compliance Engine est une plateforme d&apos;assistance à l&apos;audit documentaire de conformité juridique et technique dédiée aux textes applicables en Afrique de l&apos;Ouest (CEDEAO, UEMOA, OHADA, OAPI, Union Africaine et lois nationales).
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-900">2. Nature d&apos;aide à la décision juridique</h2>
            <p className="text-sm leading-relaxed text-slate-700">
              Les scores, constats, citations d&apos;articles et recommandations générés par la plateforme constituent un outil d&apos;analyse préparatoire. Ils doivent faire l&apos;objet d&apos;une validation humaine via le module de qualification prévu à cet effet et ne se substituent pas à une consultation juridique délivrée par un avocat ou un conseil habilité.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-900">3. Obligations de l&apos;utilisateur</h2>
            <ul className="list-disc pl-5 text-sm leading-relaxed text-slate-700 space-y-1">
              <li>Déposer uniquement des documents dont vous détenez les droits d&apos;utilisation ou l&apos;autorisation d&apos;audit.</li>
              <li>Protéger la confidentialité de vos identifiants d&apos;accès et respecter les règles d&apos;habilitation de votre organisation.</li>
              <li>Ne pas tenter de contourner les mécanismes de limitation de débit, d&apos;isolation multi-tenant ou de sécurité applicative.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-900">4. Propriété des dossiers et rapports</h2>
            <p className="text-sm leading-relaxed text-slate-700">
              L&apos;organisation utilisatrice conserve l&apos;intégralité des droits sur les documents téléversés et sur les rapports d&apos;audit générés pour ses projets.
            </p>
          </section>

          <div className="pt-4 border-t border-slate-200 flex flex-wrap gap-4 text-sm">
            <Link href="/privacy" className="text-sovereign-600 hover:underline font-medium">
              Consulter la Politique de confidentialité
            </Link>
            <Link href="/auth/register" className="text-slate-700 hover:underline">
              Créer un compte
            </Link>
          </div>
        </article>
      </main>
    </div>
  );
}
