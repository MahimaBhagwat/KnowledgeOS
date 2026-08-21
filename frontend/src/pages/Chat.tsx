import { useEffect, useState } from 'react';
import { SessionList } from '../components/chat/SessionList';
import { ChatWindow } from '../components/chat/ChatWindow';
import { chatSessionsQueryKey } from '../services/chat';
import { useQuery } from '@tanstack/react-query';
import { listSessions } from '../services/chat';

export function Chat() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const sessionsQuery = useQuery({ queryKey: chatSessionsQueryKey, queryFn: () => listSessions() });

  useEffect(() => {
    if (!selectedSessionId && sessionsQuery.data?.length) {
      setSelectedSessionId(sessionsQuery.data[0].id);
    }
  }, [selectedSessionId, sessionsQuery.data]);

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300/80">Workspace</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">AI Chat</h1>
      </div>
      <div className="grid min-h-[620px] gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="rounded-2xl border border-zinc-800 bg-zinc-950/50 p-4">
          <SessionList activeSessionId={selectedSessionId} onSelect={setSelectedSessionId} />
        </aside>
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/30 p-4">
          <ChatWindow sessionId={selectedSessionId} />
        </div>
      </div>
    </section>
  );
}
