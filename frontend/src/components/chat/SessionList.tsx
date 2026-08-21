import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  chatSessionQueryKey,
  chatSessionsQueryKey,
  createSession,
  deleteSession,
  listSessions,
  renameSession,
} from '../../services/chat';

interface SessionListProps {
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
}

export function SessionList({ activeSessionId, onSelect }: SessionListProps) {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [search, setSearch] = useState('');
  const sessionsQuery = useQuery({ queryKey: chatSessionsQueryKey, queryFn: () => listSessions() });
  const sessions = sessionsQuery.data ?? [];
  const filteredSessions = sessions.filter((session) => session.title.toLowerCase().includes(search.trim().toLowerCase()));

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: chatSessionsQueryKey });
  };
  const createMutation = useMutation({
    mutationFn: () => createSession(),
    onSuccess: (session) => {
      invalidate();
      onSelect(session.id);
    },
  });
  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => renameSession(id, title),
    onSuccess: invalidate,
  });
  const deleteMutation = useMutation({
    mutationFn: deleteSession,
    onSuccess: (_result, sessionId) => {
      invalidate();
      void queryClient.removeQueries({ queryKey: chatSessionQueryKey(sessionId) });
    },
  });

  return (
    <div className="flex h-full flex-col gap-4">
      <button type="button" className="rounded-xl bg-emerald-500 px-3 py-2 text-sm font-semibold text-zinc-950 hover:bg-emerald-400" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
        {createMutation.isPending ? 'Creating...' : '+ New Chat'}
      </button>
      <input
        type="search"
        className="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none placeholder:text-zinc-500 focus:border-emerald-400"
        placeholder="Search chats..."
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        aria-label="Search chats by title"
      />
      {sessionsQuery.isLoading ? <div className="space-y-2">{[1, 2, 3].map((item) => <div key={item} className="h-12 animate-pulse rounded-xl bg-zinc-900" />)}</div> : null}
      {sessionsQuery.isError ? <p className="text-sm text-rose-300">Failed to load chats: {sessionsQuery.error.message}</p> : null}
      <div className="space-y-2 overflow-y-auto">
        {filteredSessions.map((session) => (
          <div key={session.id} className={`rounded-xl border p-2 ${activeSessionId === session.id ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-zinc-800 bg-zinc-900/40'}`}>
            {editingId === session.id ? (
              <form className="flex gap-1" onSubmit={(event) => { event.preventDefault(); if (editingTitle.trim()) renameMutation.mutate({ id: session.id, title: editingTitle.trim() }); setEditingId(null); }}>
                <input className="min-w-0 flex-1 rounded bg-zinc-950 px-2 py-1 text-xs" value={editingTitle} onChange={(event) => setEditingTitle(event.target.value)} autoFocus />
                <button type="submit" className="text-xs text-emerald-300">Save</button>
              </form>
            ) : (
              <div className="flex items-center gap-2">
                <button type="button" className="min-w-0 flex-1 truncate text-left text-sm text-zinc-200" onClick={() => onSelect(session.id)}>{session.title}</button>
                <button type="button" className="text-xs text-zinc-500 hover:text-white" onClick={() => { setEditingId(session.id); setEditingTitle(session.title); }}>Rename</button>
                <button type="button" className="text-xs text-rose-400 hover:text-rose-300" onClick={() => { if (window.confirm('Delete this chat and all its messages?')) deleteMutation.mutate(session.id); }}>Delete</button>
              </div>
            )}
          </div>
        ))}
        {!sessionsQuery.isLoading && !sessionsQuery.isError && !filteredSessions.length ? (
          <p className="text-sm text-zinc-500">{sessions.length ? 'No chats match your search.' : 'No chats yet.'}</p>
        ) : null}
      </div>
    </div>
  );
}
