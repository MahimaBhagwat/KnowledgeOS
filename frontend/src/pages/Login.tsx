import { useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { supabase } from '../services/api';

interface LocationState {
  from?: {
    pathname?: string;
  };
}

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const fromPath = (location.state as LocationState | null)?.from?.pathname ?? '/';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (authError) {
      setError(authError.message);
      setIsSubmitting(false);
      return;
    }

    navigate(fromPath, { replace: true });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4 text-zinc-100">
      <div className="w-full max-w-md rounded-3xl border border-zinc-800 bg-zinc-900/70 p-8 shadow-2xl shadow-black/30">
        <div className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-300/80">KnowledgeOS</p>
          <h1 className="mt-2 text-3xl font-semibold">Sign in</h1>
          <p className="mt-2 text-sm text-zinc-400">Use your Supabase account to continue.</p>
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
              autoComplete="current-password"
              required
            />
          </label>

          {error ? <p className="rounded-xl border border-rose-900 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</p> : null}

          <button
            className="w-full rounded-xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-sm text-zinc-400">
          Need an account?{' '}
          <Link className="font-medium text-emerald-300 hover:text-emerald-200" to="/register">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
