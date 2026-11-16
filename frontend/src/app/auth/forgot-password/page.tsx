'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { api } from '@/lib/api';
import { Shield, Mail, Loader2, ArrowLeft, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const forgotSchema = z.object({
  email: z.string().email('Adresse email invalide'),
  website: z.string().optional(), // Honeypot anti-spam
});

type ForgotForm = z.infer<typeof forgotSchema>;

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotForm>({
    resolver: zodResolver(forgotSchema),
  });

  const onSubmit = async (data: ForgotForm) => {
    if (data.website) {
      // Bot trapped by honeypot: return silent success
      setSubmitted(true);
      return;
    }
    setIsSubmitting(true);
    setErrorMsg('');
    try {
      await api.post('/auth/forgot-password', { email: data.email });
      setSubmitted(true);
    } catch (err: any) {
      if (err?.response?.status === 429) {
        setErrorMsg('Trop de demandes effectuées. Veuillez patienter une minute.');
      } else {
        // Security best practice: do not disclose account existence
        setSubmitted(true);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <Link href="/" className="inline-flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-sovereign-500 flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" aria-hidden="true" />
            </div>
            <span className="text-xl font-bold text-slate-900">ECO-Compliance Engine</span>
          </Link>
        </div>

        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Mot de passe oublié</CardTitle>
            <CardDescription>
              Saisissez votre adresse email pour recevoir les instructions de réinitialisation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {submitted ? (
              <div className="rounded-lg border border-success-200 bg-success-50 p-4 text-center space-y-3">
                <CheckCircle className="w-8 h-8 text-success-600 mx-auto" aria-hidden="true" />
                <p className="text-sm font-medium text-success-800">
                  Si un compte est associé à cette adresse email, une demande de réinitialisation a été enregistrée.
                </p>
                <p className="text-xs text-slate-600">
                  En environnement d&apos;entreprise, votre administrateur organisationnel peut également réinitialiser l&apos;accès si le relais SMTP n&apos;est pas configuré.
                </p>
                <Link href="/auth/login" className="btn-primary w-full mt-2">
                  Retour à la connexion
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                {errorMsg && (
                  <p role="alert" className="rounded-md border border-danger-300 bg-danger-50 p-3 text-sm text-danger-800">
                    {errorMsg}
                  </p>
                )}

                {/* Honeypot anti-spam invisible */}
                <div className="hidden" aria-hidden="true">
                  <label htmlFor="website">Site web</label>
                  <input id="website" type="text" tabIndex={-1} autoComplete="off" {...register('website')} />
                </div>

                <div>
                  <Label htmlFor="email">Adresse email</Label>
                  <div className="relative mt-1">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" aria-hidden="true" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="vous@exemple.com"
                      className={cn('pl-10', errors.email && 'input-error')}
                      {...register('email')}
                      disabled={isSubmitting}
                    />
                  </div>
                  {errors.email && (
                    <p className="mt-1 text-sm text-danger-600">{errors.email.message}</p>
                  )}
                </div>

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                      Envoi en cours...
                    </>
                  ) : (
                    'Envoyer le lien de réinitialisation'
                  )}
                </Button>
              </form>
            )}

            <div className="text-center">
              <Link href="/auth/login" className="text-sm text-sovereign-600 hover:underline inline-flex items-center gap-1 font-medium">
                <ArrowLeft className="w-4 h-4" aria-hidden="true" />
                Retour à la connexion
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
