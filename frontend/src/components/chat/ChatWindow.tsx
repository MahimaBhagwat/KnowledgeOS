import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { chatSessionQueryKey, chatSessionsQueryKey, getSession, renameSession, sendMessage, streamMessage } from '../../services/chat';
import { MessageBubble } from './MessageBubble';
import type { ChatMessage } from '../../types/chat';

export function ChatWindow({ sessionId }: { sessionId: string | null }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState('');
  const [optimisticMessages, setOptimisticMessages] = useState<ChatMessage[]>([]);
  const [sendError, setSendError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [firstTokenArrived, setFirstTokenArrived] = useState(false);
  const placeholderIdRef = useRef<string | null>(null);
  const autoTitledSessionIds = useRef(new Set<string>());
  const lastSentContentRef = useRef<string | null>(null);
  const sessionQuery = useQuery({
    queryKey: chatSessionQueryKey(sessionId ?? ''),
    queryFn: () => getSession(sessionId ?? ''),
    enabled: Boolean(sessionId),
  });

  useEffect(() => {
    setOptimisticMessages([]);
    setDraft('');
    setSendError(null);
  }, [sessionId]);

  const messages = useMemo(() => {
    const serverMessages = sessionQuery.data?.messages ?? [];
    return [...serverMessages, ...optimisticMessages.filter((message) => !serverMessages.some((item) => item.id === message.id))];
  }, [optimisticMessages, sessionQuery.data?.messages]);

  const sendMutation = useMutation({
    mutationFn: (content: string) => sendMessage(sessionId ?? '', content),
    onSuccess: async (assistantMessage) => {
      setDraft('');
      setSendError(null);
      // Auto-title support for non-streaming path
      try {
        const hadUserMessage = sessionQuery.data?.messages.some((m) => m.role === 'user') ?? false;
        if (sessionId && sessionQuery.data?.title === 'New Chat' && !hadUserMessage && !autoTitledSessionIds.current.has(sessionId) && lastSentContentRef.current) {
          autoTitledSessionIds.current.add(sessionId);
          const titleCandidate = (lastSentContentRef.current ?? '').slice(0, 40);
          if (titleCandidate.trim()) renameMutation.mutate({ id: sessionId, title: titleCandidate });
        }
      } catch (e) {
        // ignore
      }
      await queryClient.invalidateQueries({ queryKey: chatSessionQueryKey(sessionId ?? '') });
      setOptimisticMessages([]);
    },
    onError: (error: Error) => setSendError(error.message),
  });
  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => renameSession(id, title),
    onSuccess: (session) => {
      queryClient.setQueryData(chatSessionQueryKey(session.id), session);
      void queryClient.invalidateQueries({ queryKey: chatSessionsQueryKey });
    },
  });

  if (!sessionId) return <div className="flex h-full items-center justify-center text-sm text-zinc-400">Select a chat or create a new one.</div>;
  if (sessionQuery.isLoading) return <div className="flex h-full items-center justify-center text-sm text-zinc-400">Loading conversation...</div>;
  if (sessionQuery.isError) return <div className="text-sm text-rose-300">Failed to load conversation: {sessionQuery.error.message}</div>;

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const content = draft.trim();
    // Clear the draft immediately so the input clears as soon as the message is sent
    setDraft('');
    if (!content || isStreaming || sendMutation.isPending) return;
    const optimisticMessage: ChatMessage = {
      id: `optimistic-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content,
      prompt_tokens: null,
      completion_tokens: null,
      citations: null,
      created_at: new Date().toISOString(),
    };

    // Add optimistic user message
    setOptimisticMessages((current) => [...current, optimisticMessage]);
    setSendError(null);


    // create placeholder assistant message
    const placeholderId = `streaming-${Date.now()}`;
    placeholderIdRef.current = placeholderId;
    const placeholderAssistant: ChatMessage = {
      id: placeholderId,
      session_id: sessionId,
      role: 'assistant',
      content: '',
      prompt_tokens: null,
      completion_tokens: null,
      citations: null,
      created_at: new Date().toISOString(),
    };

    setOptimisticMessages((current) => [...current, placeholderAssistant]);
    setIsStreaming(true);
    setFirstTokenArrived(false);

    // store last sent content for possible auto-title after completion
    lastSentContentRef.current = content;
    // Start streaming; onToken appends to placeholder content
    streamMessage(sessionId ?? '', { content }, (token) => {
      setFirstTokenArrived(true);
      setOptimisticMessages((current) => current.map((m) => (m.id === placeholderId ? { ...m, content: m.content + token } : m)));
    })
      .then(async(doneMeta) => {
        // determine whether we should auto-title now: session had default title and no prior user messages
        const hadUserMessage = sessionQuery.data?.messages.some((m) => m.role === 'user') ?? false;
        if (sessionId && sessionQuery.data?.title === 'New Chat' && !hadUserMessage && !autoTitledSessionIds.current.has(sessionId)) {
          autoTitledSessionIds.current.add(sessionId);
          const titleCandidate = (lastSentContentRef.current ?? '').slice(0, 40);
          if (titleCandidate.trim()) renameMutation.mutate({ id: sessionId, title: titleCandidate });
        }

        // replace placeholder with final assistant message (server persisted)
        setDraft('');
        setSendError(null);
        setIsStreaming(false);
        setFirstTokenArrived(false);
        placeholderIdRef.current = null;
        await queryClient.invalidateQueries({ queryKey: chatSessionQueryKey(sessionId ?? '') });
        setOptimisticMessages([]);
        
      })
      .catch(async (err) => {
        // Streaming failed — fall back to non-streaming send
        setIsStreaming(false);
        setFirstTokenArrived(false);
        try {
          const assistantMessage = await sendMessage(sessionId ?? '', content);
          // determine whether we should auto-title now for fallback path
          const hadUserMessageFallback = sessionQuery.data?.messages.some((m) => m.role === 'user') ?? false;
          if (sessionQuery.data?.title === 'New Chat' && !hadUserMessageFallback && !autoTitledSessionIds.current.has(sessionId)) {
            autoTitledSessionIds.current.add(sessionId);
            const titleCandidate = (lastSentContentRef.current ?? '').slice(0, 40);
            if (titleCandidate.trim()) renameMutation.mutate({ id: sessionId, title: titleCandidate });
          }
          // remove placeholder and add returned message
          setDraft('');
          setSendError(null);
          await queryClient.invalidateQueries({ queryKey: chatSessionQueryKey(sessionId ?? '') });
          setOptimisticMessages([]);
        } catch (fallbackErr) {
          setSendError(String(fallbackErr));
        }
      });
  };

  // helper to get current placeholder content (atomic from previous state)
  function currentPlaceholderContent(currentList: ChatMessage[], placeholderId: string) {
    const p = currentList.find((m) => m.id === placeholderId && m.role === 'assistant');
    return p ? p.content : '';
  }

  return (
    <div className="flex h-full min-h-[560px] flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto pr-2">
        {!messages.length ? <div className="py-16 text-center text-sm text-zinc-400">Ask a question about your knowledge base to get started.</div> : messages.map((message) => <MessageBubble key={message.id} message={message} />)}
        {(isStreaming && !firstTokenArrived) || sendMutation.isPending ? <div className="rounded-2xl border border-zinc-800 bg-zinc-900 px-4 py-3 text-sm text-zinc-400">Assistant is thinking...</div> : null}
      </div>
      {sendError ? <p className="mt-3 rounded-xl border border-rose-900 bg-rose-500/10 p-3 text-sm text-rose-200">Message failed: {sendError}. Your draft is still available.</p> : null}
      <form className="mt-4 flex gap-2 border-t border-zinc-800 pt-4" onSubmit={handleSubmit}>
        <textarea className="min-h-12 flex-1 resize-none rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-400" placeholder="Ask KnowledgeOS..." value={draft} onChange={(event) => setDraft(event.target.value)} disabled={isStreaming || sendMutation.isPending} />
                <button type="submit" className="self-end rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-zinc-950 disabled:opacity-50" disabled={!draft.trim() || isStreaming || sendMutation.isPending}>Send</button>
      </form>
    </div>
  );
}
