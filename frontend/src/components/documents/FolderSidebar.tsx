import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { foldersQueryKey, getFolders, createFolder, renameFolder } from '../../services/documentLibrary';
import type { FolderItem } from '../../types/documents';

interface FolderSidebarProps {
  selectedFolderId: string | null;
  onSelectFolder: (folder: FolderItem) => void;
}

const SYSTEM_FOLDER_LABELS: Record<string, string> = {
  uploaded: 'System',
  quick_notes: 'System',
  archive: 'System',
};

export function FolderSidebar({ selectedFolderId, onSelectFolder }: FolderSidebarProps) {
  const {
    data: folders = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: foldersQueryKey,
    queryFn: getFolders,
  });

  useEffect(() => {
    if (!folders.length || selectedFolderId) {
      return;
    }

    const uploadedFolder = folders.find((folder) => folder.folder_type === 'uploaded');
    onSelectFolder(uploadedFolder ?? folders[0]);
  }, [folders, onSelectFolder, selectedFolderId]);

  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);

  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameName, setRenameName] = useState('');
  const [renameError, setRenameError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (name: string) => createFolder(name),
    onSuccess: (folder: FolderItem) => {
      setCreating(false);
      setNewName('');
      setCreateError(null);
      void queryClient.invalidateQueries({ queryKey: foldersQueryKey });
      onSelectFolder(folder);
    },
    onError: (err: any) => {
      setCreateError(err?.message ?? 'Failed to create folder');
    },
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => renameFolder(id, name),
    onSuccess: (folder: FolderItem) => {
      setRenamingId(null);
      setRenameName('');
      setRenameError(null);
      void queryClient.invalidateQueries({ queryKey: foldersQueryKey });
      // keep current selection if renamed folder is selected
      if (selectedFolderId === folder.id) {
        onSelectFolder(folder);
      }
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      setRenameError(typeof detail === 'string' ? detail : err?.message ?? 'Failed to rename folder');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        <div className="h-4 w-24 animate-pulse rounded bg-zinc-800" />
        <div className="h-10 animate-pulse rounded-xl bg-zinc-900/70" />
        <div className="h-10 animate-pulse rounded-xl bg-zinc-900/70" />
        <div className="h-10 animate-pulse rounded-xl bg-zinc-900/70" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-rose-900 bg-rose-500/10 p-3 text-sm text-rose-200">
        Failed to load folders: {error.message}
      </div>
    );
  }

  if (!folders.length) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 text-sm text-zinc-400">
        No folders yet. Upload a file to start building your library.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">Folders</div>
        {!creating ? (
          <button type="button" className="text-xs text-emerald-300" onClick={() => setCreating(true)}>+ New Folder</button>
        ) : null}
      </div>
      {creating ? (
        <div className="space-y-2">
          <input className="w-full rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none" placeholder="Folder name" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <div className="flex gap-2">
            <button type="button" className="rounded-xl bg-emerald-500 px-3 py-1 text-sm font-medium text-zinc-950" onClick={() => { const candidate = newName.trim(); if (!candidate) { setCreateError('Folder name cannot be empty'); return; } setCreateError(null); createMutation.mutate(candidate); }} disabled={createMutation.isPending}>Create</button>
            <button type="button" className="rounded-xl border border-zinc-700 px-3 py-1 text-sm text-zinc-300" onClick={() => { setCreating(false); setNewName(''); setCreateError(null); }}>Cancel</button>
          </div>
          {createError ? <div className="text-sm text-rose-300">{createError}</div> : null}
        </div>
      ) : null}
      <nav className="space-y-2">
        {folders.map((folder) => {
          const isActive = selectedFolderId === folder.id;
          const isSystem = folder.is_system_folder;

          const isRenaming = renamingId === folder.id;

          return (
            <div key={folder.id}>
              {!isRenaming ? (
                <button
                  type="button"
                  onClick={() => onSelectFolder(folder)}
                  className={`w-full rounded-xl border px-3 py-2 text-left transition ${
                    isActive
                      ? 'border-emerald-500/40 bg-emerald-500/10'
                      : 'border-zinc-800 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-900'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-zinc-100">{folder.name}</div>
                      <div className="text-[11px] text-zinc-400">{folder.document_count} documents</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isSystem ? (
                        <span className="rounded-full border border-emerald-700/60 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
                          {SYSTEM_FOLDER_LABELS[folder.folder_type] ?? 'System'}
                        </span>
                      ) : (
                        <>
                          <button type="button" className="text-xs text-zinc-400" onClick={(e) => { e.stopPropagation(); setRenamingId(folder.id); setRenameName(folder.name); setRenameError(null); }}>Edit</button>
                          <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-zinc-400">Custom</span>
                        </>
                      )}
                    </div>
                  </div>
                </button>
              ) : (
                <div className="w-full rounded-xl border px-3 py-2 bg-zinc-900/40">
                  <div className="flex flex-col gap-2">
                    <input className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1 text-sm" value={renameName} onChange={(e) => setRenameName(e.target.value)} />
                    <div className="flex gap-2">
                      <button type="button" className="rounded-xl bg-emerald-500 px-3 py-1 text-sm font-medium text-zinc-950" onClick={() => { const candidate = renameName.trim(); if (!candidate) { setRenameError('Folder name cannot be empty'); return; } setRenameError(null); renameMutation.mutate({ id: folder.id, name: candidate }); }} disabled={renameMutation.isPending}>Save</button>
                      <button type="button" className="rounded-xl border border-zinc-700 px-3 py-1 text-sm text-zinc-300" onClick={() => { setRenamingId(null); setRenameName(''); setRenameError(null); }}>Cancel</button>
                    </div>
                    {renameError ? <div className="text-sm text-rose-300">{renameError}</div> : null}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </div>
  );
}
