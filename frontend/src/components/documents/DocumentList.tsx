import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  documentsQueryKey,
  getDocuments,
  permanentlyDeleteDocument,
  renameDocument,
  restoreDocument,
  softDeleteDocument,
  toggleFavorite,
} from '../../services/documentLibrary';
import InsightsPanel from './InsightsPanel';
import { supabase } from '../../services/api';

interface DocumentListProps {
  folderId: string | null;
  isDeletedView?: boolean;
}

type SortOption = 'name' | 'created_at' | 'file_size';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
}

export function DocumentList({ folderId, isDeletedView = false }: DocumentListProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('created_at');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [insightsDocumentId, setInsightsDocumentId] = useState<string | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  async function handleOpen(document: { id: string }) {
    setOpenError(null);
    setOpeningId(document.id);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
      const res = await fetch(`${base}/documents/${document.id}/content`, {
        method: 'GET',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Failed to fetch document: ${res.status}`);
      }
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl);
    } catch (err: any) {
      console.error('Open document failed', err);
      setOpenError(err?.message || 'Failed to open document');
    } finally {
      setOpeningId(null);
    }
  }

  const documentsQuery = useQuery({
    queryKey: documentsQueryKey(folderId ?? '', isDeletedView),
    queryFn: () => getDocuments(folderId ?? '', { isDeleted: isDeletedView }),
    enabled: Boolean(folderId),
  });

  const invalidate = () => {
    if (folderId) {
      void queryClient.invalidateQueries({ queryKey: documentsQueryKey(folderId, isDeletedView) });
    }
  };

  const favoriteMutation = useMutation({
    mutationFn: ({ id, value }: { id: string; value: boolean }) => toggleFavorite(id, value),
    onSuccess: invalidate,
  });
  const softDeleteMutation = useMutation({ mutationFn: softDeleteDocument, onSuccess: invalidate });
  const restoreMutation = useMutation({ mutationFn: restoreDocument, onSuccess: invalidate });
  const permanentDeleteMutation = useMutation({ mutationFn: permanentlyDeleteDocument, onSuccess: invalidate });
  const renameMutation = useMutation({ mutationFn: ({ id, name }: { id: string; name: string }) => renameDocument(id, name), onSuccess: invalidate });

  const visibleDocuments = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return [...(documentsQuery.data ?? [])]
      .filter((document) => !normalizedSearch || document.name.toLowerCase().includes(normalizedSearch))
      .filter((document) => !showFavoritesOnly || document.is_favorite)
      .sort((left, right) => {
        if (sortBy === 'name') return left.name.localeCompare(right.name);
        if (sortBy === 'file_size') return right.file_size - left.file_size;
        return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
      });
  }, [documentsQuery.data, search, showFavoritesOnly, sortBy]);

  if (!folderId) {
    return <div className="rounded-2xl border border-dashed border-zinc-800 p-10 text-center text-sm text-zinc-400">Select a folder to view its documents.</div>;
  }
  if (documentsQuery.isLoading) {
    return <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-20 animate-pulse rounded-2xl bg-zinc-900/70" />)}</div>;
  }
  if (documentsQuery.isError) {
    return <div className="rounded-2xl border border-rose-900 bg-rose-500/10 p-4 text-sm text-rose-200">Failed to load documents: {documentsQuery.error.message}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row">
        <input
          className="flex-1 rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-400"
          placeholder="Search documents by name..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select className="rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-200" value={sortBy} onChange={(event) => setSortBy(event.target.value as SortOption)}>
          <option value="created_at">Newest</option>
          <option value="name">Name</option>
          <option value="file_size">File size</option>
        </select>
        {!isDeletedView ? (
          <label className="flex items-center gap-2 rounded-xl border border-zinc-700 px-3 py-2 text-sm text-zinc-300">
            <input type="checkbox" checked={showFavoritesOnly} onChange={(event) => setShowFavoritesOnly(event.target.checked)} />
            Favorites
          </label>
        ) : null}
      </div>

      {openError ? (
        <div className="rounded-md border border-rose-700 bg-rose-900/20 p-3 text-sm text-rose-200">Open failed: {openError}</div>
      ) : null}

      {!visibleDocuments.length ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-10 text-center">
          <p className="text-base font-medium text-zinc-200">{search || showFavoritesOnly ? 'No matching documents' : isDeletedView ? 'Trash is empty' : 'This folder is empty'}</p>
          <p className="mt-2 text-sm text-zinc-400">{isDeletedView ? 'Soft-deleted documents will appear here.' : 'Upload a document to see it here.'}</p>
        </div>
      ) : (
        visibleDocuments.map((document) => (
          <div key={document.id} className="flex flex-col gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex-1">
                {editingId === document.id ? (
                  <form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); if (editingName.trim()) { renameMutation.mutate({ id: document.id, name: editingName.trim() }); setEditingId(null); } }}>
                    <input className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1 text-sm" value={editingName} onChange={(event) => setEditingName(event.target.value)} autoFocus />
                    <button className="text-xs text-emerald-300" type="submit">Save</button>
                    <button className="text-xs text-zinc-400" type="button" onClick={() => setEditingId(null)}>Cancel</button>
                  </form>
                ) : (
                  <div className="flex items-center gap-2">
                    <h3 className="truncate text-sm font-medium text-zinc-100">{document.name}</h3>
                    {!isDeletedView ? <button type="button" className={document.is_favorite ? 'text-amber-300' : 'text-zinc-600'} onClick={() => favoriteMutation.mutate({ id: document.id, value: !document.is_favorite })} aria-label={document.is_favorite ? 'Remove favorite' : 'Add favorite'}>★</button> : null}
                  </div>
                )}
                <p className="mt-1 text-xs text-zinc-400">{document.file_type.toUpperCase()} · {formatFileSize(document.file_size)} · {formatDate(document.created_at)}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {!isDeletedView ? (
                  <>
                    <button type="button" className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:text-white" onClick={() => { setEditingId(document.id); setEditingName(document.name); }}>Rename</button>
                    <button type="button" className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:border-amber-700 hover:text-amber-300" onClick={() => softDeleteMutation.mutate(document.id)} disabled={softDeleteMutation.isPending}>Move to trash</button>
                    <button type="button" className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:text-sky-300" onClick={() => handleOpen(document)} disabled={openingId === document.id}>{openingId === document.id ? 'Opening...' : 'Open'}</button>
                    <button type="button" className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:text-emerald-300" onClick={() => setInsightsDocumentId(document.id)}>Insights</button>
                  </>
                ) : (
                  <>
                    <button type="button" className="rounded-lg border border-emerald-700 px-3 py-1.5 text-xs text-emerald-300" onClick={() => restoreMutation.mutate(document.id)} disabled={restoreMutation.isPending}>Restore</button>
                    <button type="button" className="rounded-lg border border-rose-800 px-3 py-1.5 text-xs text-rose-300" onClick={() => { if (window.confirm('Permanently delete this document? This cannot be undone.')) permanentDeleteMutation.mutate(document.id); }} disabled={permanentDeleteMutation.isPending}>Delete permanently</button>
                  </>
                )}
              </div>
            </div>
          </div>
        ))
      )}
      {insightsDocumentId ? <InsightsPanel documentId={insightsDocumentId} onClose={() => setInsightsDocumentId(null)} /> : null}
    </div>
  );
}
