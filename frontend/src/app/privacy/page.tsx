import type { Metadata } from 'next';
import Link from 'next/link';
import { Shield, ArrowLeft } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Politique de confidentialité',
  description:
    'Politique de protection des données à caractère personnel d’ECO-Compliance Engine conforme à la CEDEAO et à la Loi n° 2017-20.',
};

export default function PrivacyPolicyPage() {
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
              Protection des données
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">
              Politique de confidentialité
            </h1>
            <p className="text-sm text-slate-600 mt-2">
              Dernière mise à jour : 14 novembre 2026 — Référentiel : Acte additionnel CEDEAO A/SA.1/01/10 et Livre V du Code du numérique du Bénin (Loi n° 2017-20).
            </p>
          </div>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-900">1. Finalités du traitement</h2>
            <p className="text-sm leading-relaxed text-slate-700">
              ECO-Compliance Engine collecte et traite uniquement les données nécessaires à la création de votre compte, à l&apos;isolement organisationnel de vos projets, à l&apos;extraction et l&apos;analyse juridique de vos documents téléversés, ainsi qu&apos;à la génération de vos rapports d&apos;audit de conformité.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-900">2. Données collectées</h2>
            <ul className="list-disc pl-5 text-sm leading-relaxed text-slate-700 space-y-1">
              <li>Identité de connexion : adresse email, mot de passe chiffré (bcrypt), rôle dans l&apos;organisation.</li>
              <li>Données de projet : documents téléversés (PDF, DOCX, Markdown, TXT), métadonnées d&apos;analyse, contexte complémentaire et piste d&apos;audit des constats validés.</li>
              <li>Cookies essentiels : jeton d&apos;authentification (`access_token`) et préférence de consentement (`ece_cookie_consent`).</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-900">3. Cloisonnement et sécurité</h2>
            <p className="text-sm leading-relaxed text-slate-700">
              Les documents et rapports sont isolés par organisation (`org_id`) et stockés sur un stockage objet dédié (MinIO). Les administrateurs techniques de la plateforme sont soumis à une restriction d&apos;accès stricte leur interdisant l&apos;ouverture des projets et rapports privés des organisations clientes.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-900">4. Cookies et mesure d&apos;audience</h2>
            <p className="text-sm leading-relaxed text-slate-700">
              Les cookies strictement nécessaires à la session sont requis pour le fonctionnement de l&apos;authentification. Tout outil de mesure d&apos;audience éventuel n&apos;est activé qu&apos;après consentement explicite via le bandeau cookies.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-900">5. Vos droits</h2>
            <p className="text-sm leading-relaxed text-slate-700">
              Conformément aux textes applicables dans l&apos;espace CEDEAO/UEMOA, vous disposez d&apos;un droit d&apos;accès, de rectification, de portabilité et d&apos;effacement de vos données depuis les paramètres de votre compte ou en contactant l&apos;administrateur de votre organisation.
            </p>
          </section>

          <div className="pt-4 border-t border-slate-200 flex flex-wrap gap-4 text-sm">
            <Link href="/terms" className="text-sovereign-600 hover:underline font-medium">
              Consulter les Conditions Générales d&apos;Utilisation
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
