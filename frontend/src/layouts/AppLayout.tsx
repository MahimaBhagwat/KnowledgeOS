import { useMemo, useState, useEffect, useRef, type ReactNode, type MouseEvent } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  StickyNote,
  MessageSquare,
  User,
  Settings,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from 'lucide-react';

import { useApiHealth } from '../hooks/useApiHealth';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../services/api';
import { getInitialTheme, type Theme } from '../utils/theme';

interface AppLayoutProps {
  children: ReactNode;
  sidebar?: ReactNode;
}

interface UserBadgeState {
  label: string;
  initials: string;
}

function getInitials(label: string): string {
  return (
    label
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('')
      .slice(0, 2) || 'U'
  );
}

export function AppLayout({ children, sidebar }: AppLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const { isConnected, isLoading, error } = useApiHealth();
  const [logoutError, setLogoutError] = useState<string | null>(null);

  // Theme synchronization
  const [currentTheme, setCurrentTheme] = useState<Theme>(() => getInitialTheme());

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', currentTheme);

    const handleThemeChange = (e: Event) => {
      const customEvent = e as CustomEvent<Theme>;
      if (customEvent.detail) {
        setCurrentTheme(customEvent.detail);
        document.documentElement.setAttribute('data-theme', customEvent.detail);
      }
    };

    window.addEventListener('ko-theme-change', handleThemeChange);
    return () => window.removeEventListener('ko-theme-change', handleThemeChange);
  }, [currentTheme]);

  // Sidebar sizing & collapse state
  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
    const saved = localStorage.getItem('ko_sidebar_width');
    return saved ? Math.min(Math.max(Number(saved), 200), 480) : 288;
  });
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('ko_sidebar_collapsed') === 'true';
  });
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const isResizingRef = useRef(false);

  // Close mobile drawer on route changes
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  const handleMouseDown = (e: MouseEvent) => {
    e.preventDefault();
    isResizingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const handleMouseMove = (moveEvent: globalThis.MouseEvent) => {
      if (!isResizingRef.current) return;
      const newWidth = Math.min(Math.max(moveEvent.clientX, 200), 480);
      setSidebarWidth(newWidth);
      localStorage.setItem('ko_sidebar_width', String(newWidth));
    };

    const handleMouseUp = () => {
      isResizingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('ko_sidebar_collapsed', String(next));
      return next;
    });
  };

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

  const mobileNavLinks = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/documents', label: 'Documents', icon: FileText },
    { to: '/notes', label: 'Notes', icon: StickyNote },
    { to: '/chat', label: 'Chat', icon: MessageSquare },
    { to: '/profile', label: 'Profile', icon: User },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div
      className="min-h-screen text-zinc-100 flex flex-col transition-colors duration-200"
      style={{ backgroundColor: 'var(--bg-app)' }}
    >
      {/* Header - Stretches full width without mx-auto / max-w-7xl */}
      <header
        className="sticky top-0 z-30 border-b border-zinc-800/80 backdrop-blur px-4 py-2.5"
        style={{ backgroundColor: 'var(--bg-header)' }}
      >
        <div className="flex w-full items-center justify-between gap-4">
          {/* Brand & Mobile Trigger */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Toggle navigation menu"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-300 hover:text-white lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>

            <div
              onClick={() => navigate('/')}
              className="flex cursor-pointer items-center gap-2.5 select-none pl-1"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-xs font-semibold text-emerald-300 ring-1 ring-emerald-400/20">
                KO
              </div>
              <div>
                <div className="text-sm font-semibold tracking-wide text-white leading-tight">KnowledgeOS</div>
                <div className="text-[10px] text-zinc-400 leading-tight">AI workspace</div>
              </div>
            </div>
          </div>

          {/* Right Header Widgets: API Status & Profile Pill */}
          <div className="flex items-center gap-3">
            {/* API Status Badge */}
            <div className={`flex items-center gap-2 rounded-full px-3 py-1 ring-1 ${healthState.ring} bg-zinc-900/80`}>
              <span className={`h-2 w-2 rounded-full ${healthState.dot}`} />
              <span className="text-[11px] font-medium text-zinc-300">{healthState.text}</span>
            </div>

            {/* Profile Pill & Logout */}
            <div className="flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900 px-2.5 py-1">
              <button
                type="button"
                onClick={() => navigate('/profile')}
                className="flex items-center gap-2 focus:outline-none"
                title="View Profile"
              >
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/20 text-xs font-semibold text-emerald-300">
                  {userBadge.initials}
                </div>
                <div className="hidden text-left md:block">
                  <div className="truncate text-xs font-medium text-zinc-200 max-w-[140px]">{userBadge.label}</div>
                </div>
              </button>
              <button
                type="button"
                className="ml-1 flex items-center gap-1 rounded-full border border-zinc-700 px-2.5 py-0.5 text-[11px] font-medium text-zinc-300 transition hover:border-zinc-500 hover:text-white"
                onClick={handleLogout}
                aria-label="Logout"
              >
                <LogOut className="h-3 w-3 sm:hidden" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>

        {logoutError && (
          <div className="w-full px-4 pt-1 text-right text-xs text-rose-300">
            {logoutError}
          </div>
        )}
      </header>

      {/* Mobile Navigation Drawer */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Mobile Navigation">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <div
            className="fixed inset-y-0 left-0 w-64 border-r border-zinc-800 p-6 flex flex-col justify-between shadow-2xl"
            style={{ backgroundColor: 'var(--bg-app)' }}
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/20 text-xs font-bold text-emerald-300">
                    KO
                  </div>
                  <span className="font-semibold text-sm text-white">KnowledgeOS</span>
                </div>
                <button
                  type="button"
                  aria-label="Close navigation menu"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="rounded-lg p-1 text-zinc-400 hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <nav className="space-y-1">
                {mobileNavLinks.map((link) => {
                  const Icon = link.icon;
                  return (
                    <NavLink
                      key={link.to}
                      to={link.to}
                      onClick={() => setIsMobileMenuOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                          isActive
                            ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                            : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200'
                        }`
                      }
                    >
                      <Icon className="h-4 w-4" />
                      <span>{link.label}</span>
                    </NavLink>
                  );
                })}
              </nav>
            </div>

            <div className="pt-4 border-t border-zinc-800">
              <div className="flex items-center gap-2 mb-3">
                <span className={`h-2.5 w-2.5 rounded-full ${healthState.dot}`} />
                <span className="text-xs text-zinc-400">{healthState.text}</span>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900 py-2 text-xs font-medium text-zinc-200 hover:bg-zinc-800"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Workspace Layout - Edge to Edge */}
      <div className="flex flex-1 w-full flex-col lg:flex-row overflow-hidden">
        {/* Sidebar Container */}
        {sidebar && (
          <>
            <aside
              style={{
                width: isCollapsed ? 56 : sidebarWidth,
                backgroundColor: 'var(--bg-sidebar)',
              }}
              className={`relative flex-shrink-0 border-b border-zinc-800 p-3 transition-all duration-150 lg:border-b-0 lg:border-r ${
                isCollapsed ? 'overflow-hidden' : ''
              }`}
            >
              {/* Collapse Toggle Button */}
              <div className="mb-2 flex items-center justify-end">
                <button
                  type="button"
                  onClick={toggleCollapse}
                  aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                  title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                  className="flex h-7 w-7 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/80 text-zinc-400 hover:border-zinc-700 hover:text-white"
                >
                  {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                </button>
              </div>

              {!isCollapsed && sidebar}
            </aside>

            {/* Draggable Splitter Handle */}
            {!isCollapsed && (
              <div
                onMouseDown={handleMouseDown}
                aria-label="Resize sidebar"
                role="separator"
                className="hidden lg:block w-1 cursor-col-resize bg-transparent hover:bg-emerald-500/40 active:bg-emerald-500 transition-colors"
              />
            )}
          </>
        )}

        {/* Main Content Area */}
        <main
          className="flex-1 overflow-y-auto px-6 py-6 lg:px-12 lg:py-8"
          style={{ backgroundColor: 'var(--bg-app)' }}
        >
          <div
            className="mx-auto max-w-5xl rounded-2xl border border-zinc-800/90 p-6 sm:p-8 shadow-2xl shadow-black/20 min-h-[calc(100vh-120px)]"
            style={{ backgroundColor: 'var(--bg-card)' }}
          >
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
