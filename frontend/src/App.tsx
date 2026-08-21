import { BrowserRouter, Navigate, Outlet, Route, Routes, NavLink } from 'react-router-dom';

import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { PublicRoute } from './components/PublicRoute';
import { AppLayout } from './layouts/AppLayout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Documents } from './pages/Documents';
import { Chat } from './pages/Chat';
import { Notes } from './pages/Notes';

function Home() {
  return (
    <section className="space-y-4">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300/80">Workspace</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Home</h1>
      </div>
      <p className="max-w-2xl text-sm leading-6 text-zinc-300">
        This is the KnowledgeOS frontend shell. Use the sidebar to navigate workspace sections as the app grows.
      </p>
    </section>
  );
}

function WorkspaceLayout() {
  return (
    <AppLayout
      sidebar={
        <nav className="space-y-2">
          <div className="px-2 text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">Navigation</div>
          <NavLink
            to="/"
            className={({ isActive }) =>
              `flex items-center rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
            end
          >
            Home
          </NavLink>
          <NavLink
            to="/documents"
            className={({ isActive }) =>
              `flex items-center rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
          >
            Documents
          </NavLink>
          <NavLink
            to="/chat"
            className={({ isActive }) =>
              `flex items-center rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
          >
            Chat
          </NavLink>
          <NavLink
            to="/notes"
            className={({ isActive }) =>
              `flex items-center rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
          >
            Notes
          </NavLink>
        </nav>
      }
    >
      <Outlet />
    </AppLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicRoute />}>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<WorkspaceLayout />}>
              <Route index element={<Home />} />
              <Route path="documents" element={<Documents />} />
              <Route path="chat" element={<Chat />} />
              <Route path="notes" element={<Notes />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
