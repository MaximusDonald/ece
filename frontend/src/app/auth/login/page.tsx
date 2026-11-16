'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useLogin } from '@/hooks/useApi';
import { authApi } from '@/lib/api';
import { Shield, Mail, Lock, Eye, EyeOff, Loader2 } from 'lucide-react';
import { cn, getApiErrorMessage } from '@/lib/utils';

const loginSchema = z.object({
  email: z.string().email('Email invalide'),
  password: z.string().min(8, 'Le mot de passe doit contenir au moins 8 caractères'),
  remember: z.boolean().optional(),
  website: z.string().optional(), // Honeypot anti-spam
});

type LoginForm = z.infer<typeof loginSchema>;

function LoginFormPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const loginMutation = useLogin();
  const queryClient = useQueryClient();
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState('');
  const accountCreated = searchParams.get('registered') === '1';
  const callbackUrl = searchParams.get('callbackUrl') || '/dashboard';

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { remember: true },
  });

  const onSubmit = async (data: LoginForm) => {
    if (data.website) {
      return;
    }
    setLoginError('');
    try {
      await loginMutation.mutateAsync({ email: data.email, password: data.password });
      const currentUser = await authApi.getMe();
      queryClient.setQueryData(['me'], currentUser);
      const isPlatformAdmin = currentUser.is_superuser || currentUser.role === 'platform_admin';
      const destination = callbackUrl === '/dashboard' && isPlatformAdmin
        ? '/dashboard/admin/users'
        : callbackUrl;
      router.replace(destination);
      router.refresh();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setLoginError(
        detail === 'LOGIN_BAD_CREDENTIALS'
          ? 'Adresse email ou mot de passe incorrect.'
          : getApiErrorMessage(err, 'Connexion impossible. Vérifiez votre adresse email et votre mot de passe, puis réessayez.')
      );
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Left branding - hidden on mobile */}
        <div className="hidden lg:block mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-sovereign-500 flex items-center justify-center">
              <Shield className="w-7 h-7 text-white" />
            </div>
            <span className="text-2xl font-bold text-slate-900">ECE</span>
          </div>
          <p className="text-slate-600">ECO-Compliance Engine — Audit documentaire souverain</p>
        </div>

        {/* Login Card */}
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Connexion</CardTitle>
            <CardDescription>Accédez à votre espace de conformité</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <form method="post" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Honeypot anti-spam invisible */}
              <div className="hidden" aria-hidden="true">
                <label htmlFor="website">Site web</label>
                <input id="website" type="text" tabIndex={-1} autoComplete="off" {...register('website')} />
              </div>
              {accountCreated && (
                <p role="status" className="rounded-md border border-success-300 bg-success-50 p-3 text-sm text-success-800">
                  Votre compte est créé. Connectez-vous avec vos identifiants.
                </p>
              )}
              {loginError && (
                <p role="alert" className="rounded-md border border-danger-300 bg-danger-50 p-3 text-sm text-danger-900">
                  {loginError}
                </p>
              )}
              <div>
                <Label htmlFor="email">Email</Label>
                <div className="relative mt-1">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="vous@exemple.com"
                    className={cn('pl-10', errors.email && 'input-error')}
                    {...register('email')}
                    disabled={loginMutation.isPending}
                  />
                </div>
                {errors.email && (
                  <p className="mt-1 text-sm text-danger-600">{errors.email.message}</p>
                )}
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Mot de passe</Label>
                  <Link href="/auth/forgot-password" className="text-sm text-sovereign-600 hover:underline">
                    Mot de passe oublié ?
                  </Link>
                </div>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    className={cn('pl-10 pr-10', errors.password && 'input-error')}
                    {...register('password')}
                    disabled={loginMutation.isPending}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="mt-1 text-sm text-danger-600">{errors.password.message}</p>
                )}
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    {...register('remember')}
                    className="h-4 w-4 text-sovereign-500 border-slate-300 rounded focus:ring-sovereign-500"
                  />
                  <span className="text-sm text-slate-600">Se souvenir de moi</span>
                </label>
              </div>

              <Button type="submit" className="w-full" disabled={loginMutation.isPending}>
                {loginMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Connexion...
                  </>
                ) : (
                  'Se connecter'
                )}
              </Button>
            </form>

            <p className="text-center text-sm text-slate-600">
              Pas de compte ?{' '}
              <Link href="/auth/register" className="text-sovereign-600 hover:underline font-medium">
                S'inscrire
              </Link>
            </p>
          </CardContent>
        </Card>

        <div className="text-center text-xs text-slate-600 mt-6 space-y-1">
          <p>ECO-Compliance Engine — Plateforme souveraine d&apos;audit documentaire</p>
          <p className="space-x-3">
            <Link href="/terms" className="text-sovereign-600 hover:underline">CGU</Link>
            <span>·</span>
            <Link href="/privacy" className="text-sovereign-600 hover:underline">Politique de confidentialité</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-50" />}>
      <LoginFormPage />
    </Suspense>
  );
}
