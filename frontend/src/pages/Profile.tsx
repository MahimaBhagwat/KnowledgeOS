import { useState, type FormEvent } from 'react';
import { User, Mail, Check, ShieldCheck } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../services/api';

export function Profile() {
  const { user } = useAuth();
  const [fullName, setFullName] = useState(user?.user_metadata?.full_name || '');
  const [isUpdating, setIsUpdating] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleUpdateProfile = async (e: FormEvent) => {
    e.preventDefault();
    setIsUpdating(true);
    setStatusMessage(null);

    const { error } = await supabase.auth.updateUser({
      data: { full_name: fullName.trim() },
    });

    setIsUpdating(false);
    if (error) {
      setStatusMessage({ type: 'error', text: error.message });
    } else {
      setStatusMessage({ type: 'success', text: 'Profile updated successfully.' });
    }
  };

  const initials = (fullName || user?.email || 'U')
    .split(/\s+/)
    .filter(Boolean)
    .map((p: string) => p[0]?.toUpperCase() ?? '')
    .join('')
    .slice(0, 2) || 'U';

  return (
    <section className="space-y-6" aria-label="User Profile">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300/80">Account</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">User Profile</h1>
        <p className="mt-2 text-sm text-zinc-400">Manage your identity and workspace preferences.</p>
      </div>

      <div className="rounded-3xl border border-zinc-800 bg-zinc-950/60 p-6 sm:p-8" role="region" aria-label="Account details">
        <div className="flex flex-col items-start gap-6 sm:flex-row sm:items-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-emerald-500/15 text-2xl font-bold text-emerald-300 ring-2 ring-emerald-400/20">
            {initials}
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">{fullName || 'KnowledgeOS User'}</h2>
            <p className="text-sm text-zinc-400 flex items-center gap-1.5 mt-0.5">
              <Mail className="h-3.5 w-3.5 text-zinc-500" />
              <span>{user?.email}</span>
            </p>
            <div className="mt-2.5 flex flex-wrap gap-2">
              <span className="flex items-center gap-1 rounded-full border border-emerald-700/60 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Active Member</span>
              </span>
              <span className="rounded-full border border-zinc-700 bg-zinc-900 px-2.5 py-0.5 text-xs text-zinc-400">
                User ID: {user?.id?.slice(0, 8)}...
              </span>
            </div>
          </div>
        </div>

        <hr className="my-6 border-zinc-800" />

        <form onSubmit={handleUpdateProfile} className="max-w-md space-y-4">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-zinc-300">Full Name</span>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm text-zinc-100 outline-none transition focus-visible:border-emerald-400 focus-visible:ring-2 focus-visible:ring-emerald-400"
              placeholder="Your full name"
              aria-label="Full Name"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-zinc-300">Email Address</span>
            <input
              type="email"
              value={user?.email || ''}
              disabled
              className="w-full rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-2.5 text-sm text-zinc-500 cursor-not-allowed"
              aria-label="Email Address (read-only)"
            />
            <p className="text-[11px] text-zinc-500">Email address cannot be modified from this screen.</p>
          </label>

          {statusMessage && (
            <div
              className={`rounded-xl border p-3 text-sm ${
                statusMessage.type === 'success'
                  ? 'border-emerald-900 bg-emerald-500/10 text-emerald-200'
                  : 'border-rose-900 bg-rose-500/10 text-rose-200'
              }`}
              role="status"
            >
              {statusMessage.text}
            </div>
          )}

          <button
            type="submit"
            disabled={isUpdating}
            className="flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-400 focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:outline-none disabled:opacity-50"
          >
            <Check className="h-4 w-4" />
            <span>{isUpdating ? 'Saving...' : 'Save Profile'}</span>
          </button>
        </form>
      </div>
    </section>
  );
}
