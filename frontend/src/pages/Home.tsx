import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Search,
  Files,
  StickyNote,
  MessageSquare,
  Sparkles,
  Plus,
  Upload,
  FilePlus,
  Settings as SettingsIcon,
  ArrowUpRight,
  FileText,
} from 'lucide-react';

import { getDocuments } from '../services/documentLibrary';
import { listSessions } from '../services/chat';
import { listNotes } from '../services/notes';
import { api } from '../services/api';
import type { DocumentItem } from '../types/documents';
import type { ChatSession } from '../types/chat';
import type { Note } from '../types/notes';

interface SearchResult {
  id: string;
  parent_id: string;
  title: string;
  snippet: string;
  source_type: 'document' | 'note';
  similarity_score: number;
}

export function Home() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const docsQuery = useQuery({ queryKey: ['documents', 'all'], queryFn: () => getDocuments() });
  const chatQuery = useQuery({ queryKey: ['chat-sessions'], queryFn: () => listSessions() });
  const notesQuery = useQuery({ queryKey: ['notes'], queryFn: () => listNotes() });

  const totalDocs = docsQuery.data?.length ?? 0;
  const totalChats = chatQuery.data?.length ?? 0;
  const totalNotes = notesQuery.data?.length ?? 0;

  const handleGlobalSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (!q) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    setSearchError(null);
    try {
      const response = await api.post('/search', { query: q, top_k: 8 });
      setSearchResults(response.data?.results ?? []);
    } catch (err: any) {
      setSearchError(err?.response?.data?.detail || err?.message || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <section className="space-y-8" aria-label="KnowledgeOS Dashboard">
      {/* Header */}
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300/80">Dashboard</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">Knowledge Workspace</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Intelligent AI workspace powered by vector embeddings and structured multi-document synthesis.
        </p>
      </div>

      {/* Global Hybrid Search Bar */}
      <div className="rounded-2xl border border-zinc-800/90 p-4 shadow-lg sm:p-6" style={{ backgroundColor: 'var(--bg-card)' }}>
        <form onSubmit={handleGlobalSearch} className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <input
              type="search"
              aria-label="Search all documents and notes"
              placeholder="Search across all documents, chunks, and notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-zinc-700 bg-zinc-900/90 pl-11 pr-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition focus-visible:border-emerald-400 focus-visible:ring-2 focus-visible:ring-emerald-400"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching}
            className="flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-400 disabled:opacity-50"
            aria-label="Execute Hybrid Search"
          >
            <Search className="h-4 w-4" />
            <span>{isSearching ? 'Searching...' : 'Hybrid Search'}</span>
          </button>
        </form>

        {searchError && (
          <p className="mt-3 rounded-lg border border-rose-900 bg-rose-500/10 p-2 text-xs text-rose-300">
            {searchError}
          </p>
        )}

        {searchResults.length > 0 && (
          <div className="mt-4 space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Search Results ({searchResults.length})
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {searchResults.map((res) => (
                <div
                  key={res.id}
                  onClick={() => {
                    if (res.source_type === 'note') navigate('/notes');
                    else navigate('/documents');
                  }}
                  className="cursor-pointer rounded-xl border border-zinc-800 bg-zinc-900/70 p-3 transition hover:border-emerald-500/50 hover:bg-zinc-900"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium text-zinc-100">{res.title}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        res.source_type === 'note'
                          ? 'border border-blue-500/40 bg-blue-500/10 text-blue-300'
                          : 'border border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                      }`}
                    >
                      {res.source_type}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs text-zinc-400">{res.snippet}</p>
                  <div className="mt-2 text-[10px] text-zinc-500">
                    Relevance: {(res.similarity_score * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div
          onClick={() => navigate('/documents')}
          className="group cursor-pointer rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 transition hover:border-emerald-500/30 hover:bg-zinc-900"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">Uploaded Documents</span>
            <Files className="h-5 w-5 text-emerald-400 transition group-hover:scale-110" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">{totalDocs}</div>
          <p className="mt-1 text-xs text-emerald-400/90">Processed & Chunked</p>
        </div>

        <div
          onClick={() => navigate('/notes')}
          className="group cursor-pointer rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 transition hover:border-emerald-500/30 hover:bg-zinc-900"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">Quick Notes</span>
            <StickyNote className="h-5 w-5 text-blue-400 transition group-hover:scale-110" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">{totalNotes}</div>
          <p className="mt-1 text-xs text-blue-400/90">Indexed for Vector RAG</p>
        </div>

        <div
          onClick={() => navigate('/chat')}
          className="group cursor-pointer rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 transition hover:border-emerald-500/30 hover:bg-zinc-900"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">Chat Sessions</span>
            <MessageSquare className="h-5 w-5 text-amber-400 transition group-hover:scale-110" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">{totalChats}</div>
          <p className="mt-1 text-xs text-amber-400/90">Interactive AI Conversations</p>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-zinc-400">AI Intelligence</span>
            <Sparkles className="h-5 w-5 text-emerald-300" />
          </div>
          <div className="mt-3 text-3xl font-bold text-emerald-300">Active</div>
          <p className="mt-1 text-xs text-zinc-400">Hybrid RAG + Multi-Doc Insights</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">Quick Actions</h2>
        <div className="mt-3 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-400"
            aria-label="Start new AI Chat"
          >
            <Plus className="h-4 w-4" />
            <span>New AI Chat</span>
          </button>
          <button
            type="button"
            onClick={() => navigate('/documents')}
            className="flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500 hover:text-white"
            aria-label="Upload Documents"
          >
            <Upload className="h-4 w-4" />
            <span>Upload Documents</span>
          </button>
          <button
            type="button"
            onClick={() => navigate('/notes')}
            className="flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500 hover:text-white"
            aria-label="Create Quick Note"
          >
            <FilePlus className="h-4 w-4" />
            <span>Create Quick Note</span>
          </button>
          <button
            type="button"
            onClick={() => navigate('/settings')}
            className="flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:border-zinc-500 hover:text-white"
            aria-label="Open System Settings"
          >
            <SettingsIcon className="h-4 w-4" />
            <span>System Settings</span>
          </button>
        </div>
      </div>

      {/* Recent Activity Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Documents */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-200">Recent Documents</h3>
            <button
              onClick={() => navigate('/documents')}
              className="flex items-center gap-1 text-xs text-emerald-400 hover:underline"
              aria-label="View all documents"
            >
              <span>View all</span>
              <ArrowUpRight className="h-3 w-3" />
            </button>
          </div>
          <div className="mt-3 space-y-2">
            {(docsQuery.data as DocumentItem[] | undefined)?.slice(0, 4).map((doc) => (
              <div
                key={doc.id}
                onClick={() => navigate('/documents')}
                className="cursor-pointer rounded-xl border border-zinc-800/80 bg-zinc-950/50 p-3 transition hover:border-zinc-700"
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 flex-shrink-0 text-emerald-400" />
                  <span className="truncate text-xs font-medium text-zinc-200">{doc.name}</span>
                </div>
                <div className="mt-1 flex items-center justify-between pl-5.5 text-[10px] text-zinc-500">
                  <span>{(doc.file_size / 1024).toFixed(0)} KB</span>
                  <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
            {!docsQuery.data?.length && (
              <p className="text-xs text-zinc-500">No documents uploaded yet.</p>
            )}
          </div>
        </div>

        {/* Recent Notes */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-200">Recent Notes</h3>
            <button
              onClick={() => navigate('/notes')}
              className="flex items-center gap-1 text-xs text-emerald-400 hover:underline"
              aria-label="View all notes"
            >
              <span>View all</span>
              <ArrowUpRight className="h-3 w-3" />
            </button>
          </div>
          <div className="mt-3 space-y-2">
            {(notesQuery.data as Note[] | undefined)?.slice(0, 4).map((note) => (
              <div
                key={note.id}
                onClick={() => navigate('/notes')}
                className="cursor-pointer rounded-xl border border-zinc-800/80 bg-zinc-950/50 p-3 transition hover:border-zinc-700"
              >
                <div className="flex items-center gap-2">
                  <StickyNote className="h-3.5 w-3.5 flex-shrink-0 text-blue-400" />
                  <span className="truncate text-xs font-medium text-zinc-200">{note.title}</span>
                </div>
                <p className="mt-1 line-clamp-1 pl-5.5 text-[11px] text-zinc-400">{note.content}</p>
                <div className="mt-1 pl-5.5 text-[10px] text-zinc-500">
                  {new Date(note.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
            {!notesQuery.data?.length && (
              <p className="text-xs text-zinc-500">No quick notes yet.</p>
            )}
          </div>
        </div>

        {/* Recent Chat Sessions */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-zinc-200">Recent Conversations</h3>
            <button
              onClick={() => navigate('/chat')}
              className="flex items-center gap-1 text-xs text-emerald-400 hover:underline"
              aria-label="Open all chats"
            >
              <span>Open chat</span>
              <ArrowUpRight className="h-3 w-3" />
            </button>
          </div>
          <div className="mt-3 space-y-2">
            {(chatQuery.data as ChatSession[] | undefined)?.slice(0, 4).map((session) => (
              <div
                key={session.id}
                onClick={() => navigate('/chat')}
                className="cursor-pointer rounded-xl border border-zinc-800/80 bg-zinc-950/50 p-3 transition hover:border-zinc-700"
              >
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-3.5 w-3.5 flex-shrink-0 text-amber-400" />
                  <span className="truncate text-xs font-medium text-zinc-200">{session.title}</span>
                </div>
                <div className="mt-1 pl-5.5 text-[10px] text-zinc-500">
                  {new Date(session.updated_at).toLocaleDateString()}
                </div>
              </div>
            ))}
            {!chatQuery.data?.length && (
              <p className="text-xs text-zinc-500">No chat sessions yet.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
