import { BrowserRouter, Navigate, Outlet, Route, Routes, NavLink } from 'react-router-dom';

import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { PublicRoute } from './components/PublicRoute';
import { AppLayout } from './layouts/AppLayout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Home } from './pages/Home';
import { Documents } from './pages/Documents';
import { Chat } from './pages/Chat';
import { Notes } from './pages/Notes';
import { Profile } from './pages/Profile';
import { Settings } from './pages/Settings';

import {
  LayoutDashboard,
  FileText,
  StickyNote,
  MessageSquare,
  User,
  Settings as SettingsIcon,
} from 'lucide-react';

function WorkspaceLayout() {
  return (
    <AppLayout
      sidebar={
        <nav className="space-y-1.5" aria-label="Main Navigation">
          <div className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
            Workspace
          </div>
          <NavLink
            to="/"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300 font-medium' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
            end
          >
            <LayoutDashboard className="h-4 w-4" />
            <span>Dashboard</span>
          </NavLink>
          <NavLink
            to="/documents"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300 font-medium' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
          >
            <FileText className="h-4 w-4" />
            <span>Documents</span>
          </NavLink>
          <NavLink
            to="/notes"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300 font-medium' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
          >
            <StickyNote className="h-4 w-4" />
            <span>Notes</span>
          </NavLink>
          <NavLink
            to="/chat"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300 font-medium' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
          >
            <MessageSquare className="h-4 w-4" />
            <span>Chat</span>
          </NavLink>

          <div className="px-2 pt-4 pb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
            Preferences
          </div>
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300 font-medium' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
          >
            <User className="h-4 w-4" />
            <span>Profile</span>
          </NavLink>
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition ${
                isActive ? 'bg-emerald-500/15 text-emerald-300 font-medium' : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
              }`
            }
          >
            <SettingsIcon className="h-4 w-4" />
            <span>Settings</span>
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
              <Route path="profile" element={<Profile />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
