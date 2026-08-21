import { useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { useApiHealth } from '../hooks/useApiHealth';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../services/api';

interface AppLayoutProps {
  children: ReactNode;
  sidebar?: ReactNode;
}

interface UserBadgeState {
  label: string;
  initials: string;
}

function getInitials(label: string): string {
  return label
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
    .slice(0, 2) || 'U';
}

export function AppLayout({ children, sidebar }: AppLayoutProps) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isConnected, isLoading, error } = useApiHealth();
  const [logoutError, setLogoutError] = useState<string | null>(null);

  const label = user?.user_metadata?.full_name || user?.email || 'KnowledgeOS User';
  const userBadge: UserBadgeState = {
    label,
    initials: getInitials(label),
  };

  const handleLogout = async () => {
    setLogoutError(null);
    const { error: signOutError } = await supabase.auth.signOut();

    if (signOutError) {
      setLogoutError(signOutError.message);
      return;
    }

    navigate('/login', { replace: true });
  };

  const healthState = useMemo(() => {
    if (isLoading) {
      return {
        dot: 'bg-amber-400',
        text: 'Checking API',
        ring: 'ring-amber-400/20',
      };
    }

    if (isConnected) {
      return {
        dot: 'bg-emerald-400',
        text: 'API Online',
        ring: 'ring-emerald-400/20',
      };
    }

    const isUnauthorized = error?.toLowerCase().includes('unauthorized') ?? false;

    return {
      dot: isUnauthorized ? 'bg-amber-400' : 'bg-rose-400',
      text: isUnauthorized ? 'Unauthorized' : 'API Offline',
      ring: isUnauthorized ? 'ring-amber-400/20' : 'ring-rose-400/20',
    };
  }, [error, isConnected, isLoading]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800/80 bg-zinc-950/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 text-sm font-semibold text-emerald-300 ring-1 ring-emerald-400/20">
              KO
            </div>
            <div>
              <div className="text-sm font-semibold tracking-wide text-white">KnowledgeOS</div>
              <div className="text-xs text-zinc-400">AI workspace</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-2 rounded-full px-3 py-1.5 ring-1 ${healthState.ring} bg-zinc-900/80`}>
              <span className={`h-2.5 w-2.5 rounded-full ${healthState.dot}`} />
              <span className="text-xs font-medium text-zinc-200">{healthState.text}</span>
            </div>

            <div className="flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-zinc-800 text-xs font-semibold text-zinc-200">
                {userBadge.initials}
              </div>
              <div className="hidden text-right sm:block">
                <div className="text-xs font-medium text-zinc-100">{userBadge.label}</div>
                <div className="text-[11px] text-zinc-400">{error ? 'Connection issue' : 'Workspace profile'}</div>
              </div>
              <button
                type="button"
                className="ml-2 rounded-full border border-zinc-700 px-3 py-1 text-[11px] font-medium text-zinc-200 transition hover:border-zinc-500 hover:text-white"
                onClick={handleLogout}
              >
                Logout
              </button>
            </div>
          </div>
        </div>
        {logoutError ? (
          <div className="mx-auto max-w-7xl px-4 pb-4 text-right text-xs text-rose-300 sm:px-6 lg:px-8">
            {logoutError}
          </div>
        ) : null}
      </header>

      <div className="mx-auto flex min-h-[calc(100vh-73px)] max-w-7xl flex-col lg:flex-row">
        <aside className="border-b border-zinc-800 bg-zinc-950/60 p-4 lg:w-80 lg:border-b-0 lg:border-r">
          {sidebar ?? (
            <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/40 p-4 text-sm text-zinc-500">
              Sidebar slot
            </div>
          )}
        </aside>

        <main className="flex-1 bg-zinc-950 p-4 sm:p-6 lg:p-8">
          <div className="rounded-3xl border border-zinc-800 bg-zinc-900/40 p-4 shadow-2xl shadow-black/20 sm:p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
