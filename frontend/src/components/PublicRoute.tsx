import { Navigate, Outlet } from 'react-router-dom';

import { useAuth } from '../contexts/AuthContext';

export function PublicRoute() {
  const { session, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-300">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 px-4 py-3 text-sm">Loading...</div>
      </div>
    );
  }

  if (session) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
