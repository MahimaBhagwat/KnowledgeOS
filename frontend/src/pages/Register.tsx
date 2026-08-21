import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { supabase } from '../services/api';

export function Register() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setStatusMessage(null);

    const { data, error: authError } = await supabase.auth.signUp({
      email,
      password,
    });

    if (authError) {
      setError(authError.message);
      setIsSubmitting(false);
      return;
    }

    if (data.session) {
      navigate('/', { replace: true });
      return;
    }

    setStatusMessage('Account created. Please check your email to confirm your registration before signing in.');
    setIsSubmitting(false);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4 text-zinc-100">
      <div className="w-full max-w-md rounded-3xl border border-zinc-800 bg-zinc-900/70 p-8 shadow-2xl shadow-black/30">
        <div className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-300/80">KnowledgeOS</p>
          <h1 className="mt-2 text-3xl font-semibold">Create account</h1>
          <p className="mt-2 text-sm text-zinc-400">Register with Supabase Auth.</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <label className="block space-y-2">
            <span className="text-sm text-zinc-300">Email</span>
            <input
              className="w-full rounded-xl border border-zinc-700 bg-zinc-950 px-4 py-3 text-sm outline-none transition focus:border-emerald-400"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm text-zinc-300">Password</span>
            <input
              className="w-full rounded-xl border border-zinc-700 bg-zinc-950 px-4 py-3 text-sm outline-none transition focus:border-emerald-400"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
              required
            />
          </label>

          {error ? <p className="rounded-xl border border-rose-900 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</p> : null}
          {statusMessage ? (
            <p className="rounded-xl border border-emerald-900 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
              {statusMessage}
            </p>
          ) : null}

          <button
            className="w-full rounded-xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <p className="mt-6 text-sm text-zinc-400">
          Already have an account?{' '}
          <Link className="font-medium text-emerald-300 hover:text-emerald-200" to="/login">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
