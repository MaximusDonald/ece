'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useRegister } from '@/hooks/useApi';
import { Shield, Mail, Lock, Loader2, Eye, EyeOff } from 'lucide-react';
import { toast } from '@/hooks/use-toast';
import { getApiErrorMessage } from '@/lib/utils';
import { passwordStrengthColor, passwordStrengthLabel, passwordStrengthScore } from '@/lib/password-strength';

const MIN_PASSWORD_STRENGTH = 7;

const registerSchema = z.object({
  email: z.string().email('Email invalide'),
  password: z.string()
    .min(8, 'Le mot de passe doit contenir au moins 8 caractères')
    .refine((password) => new TextEncoder().encode(password).length <= 72, 'Le mot de passe ne peut pas dépasser 72 octets.')
    .refine(
      (password) => passwordStrengthScore(password) >= MIN_PASSWORD_STRENGTH,
      (password) => ({
        message: `Le mot de passe doit atteindre au moins 7/10 (score actuel : ${passwordStrengthScore(password)}/10).`,
      }),
    ),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Les mots de passe ne correspondent pas',
  path: ['confirmPassword'],
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const registerMutation = useRegister();
  const [showPassword, setShowPassword] = useState(false);

  const { register, handleSubmit, watch, formState: { errors, isValid } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    mode: 'onChange',
  });
  const password = watch('password', '');
  const passwordScore = passwordStrengthScore(password);
  const passwordColor = passwordStrengthColor(passwordScore);

  const onSubmit = async (data: RegisterForm) => {
    try {
      await registerMutation.mutateAsync({ email: data.email, password: data.password });
      toast({ title: 'Inscription réussie', description: 'Bienvenue sur ECE !' });
      router.push('/auth/login?registered=1');
      router.refresh();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      toast({ 
        title: 'Erreur d\'inscription', 
        description: detail === 'REGISTER_USER_ALREADY_EXISTS'
          ? 'Cette adresse email est déjà associée à un compte.'
          : getApiErrorMessage(err, 'La création du compte a échoué. Vérifiez les informations puis réessayez.'),
        variant: 'destructive' 
      });
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Branding */}
        <div className="hidden lg:block mb-8 text-center">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-sovereign-500 flex items-center justify-center">
              <Shield className="w-7 h-7 text-white" />
            </div>
            <span className="text-2xl font-bold text-slate-900">ECE</span>
          </div>
          <p className="text-slate-600">ECO-Compliance Engine — Audit documentaire souverain</p>
        </div>

        {/* Register Card */}
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Créer un compte</CardTitle>
            <CardDescription>Rejoignez la plateforme d'audit de conformité souverain</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
                    disabled={registerMutation.isPending}
                  />
                </div>
                {errors.email && (
                  <p className="mt-1 text-sm text-danger-600">{errors.email.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="password">Mot de passe</Label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    className={cn('pl-10 pr-10', errors.password && 'input-error')}
                    {...register('password')}
                    disabled={registerMutation.isPending}
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
                <div className="mt-2" aria-live="polite">
                  <div className="flex items-center justify-between text-xs text-slate-600">
                    <span>Force : {passwordStrengthLabel(passwordScore)}</span>
                    <span>{passwordScore}/10 · minimum 7/10</span>
                  </div>
                  <div
                    className="mt-1 flex gap-1"
                    role="progressbar"
                    aria-label="Force du mot de passe"
                    aria-valuemin={0}
                    aria-valuemax={10}
                    aria-valuenow={passwordScore}
                  >
                    {Array.from({ length: 10 }, (_, index) => (
                      <span
                        key={index}
                        className={`h-1.5 flex-1 rounded-full ${index < passwordScore ? passwordColor : 'bg-slate-200'}`}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <Label htmlFor="confirmPassword">Confirmer le mot de passe</Label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    id="confirmPassword"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    className={cn('pl-10', errors.confirmPassword && 'input-error')}
                    {...register('confirmPassword')}
                    disabled={registerMutation.isPending}
                  />
                </div>
                {errors.confirmPassword && (
                  <p className="mt-1 text-sm text-danger-600">{errors.confirmPassword.message}</p>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={registerMutation.isPending || !isValid}>
                {registerMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Création du compte...
                  </>
                ) : (
                  'Créer mon compte'
                )}
              </Button>
            </form>

            <p className="text-center text-sm text-slate-600">
              Déjà un compte ?{' '}
              <Link href="/auth/login" className="text-sovereign-600 hover:underline font-medium">
                Se connecter
              </Link>
            </p>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-slate-400 mt-6">
          En créant un compte, vous acceptez nos <Link href="/terms" className="text-sovereign-600 hover:underline">CGU</Link> et notre <Link href="/privacy" className="text-sovereign-600 hover:underline">politique de confidentialité</Link>.
        </p>
      </div>
    </div>
  );
}

import { cn } from '@/lib/utils';
