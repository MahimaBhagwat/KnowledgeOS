import { useCallback, useState } from 'react';

import { DocumentList } from '../components/documents/DocumentList';
import { FolderSidebar } from '../components/documents/FolderSidebar';
import { UploadDialog } from '../components/documents/UploadDialog';
import type { FolderItem } from '../types/documents';

export function Documents() {
  const [selectedFolder, setSelectedFolder] = useState<FolderItem | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isDeletedView, setIsDeletedView] = useState(false);

  const handleSelectFolder = useCallback((folder: FolderItem) => {
    setSelectedFolder(folder);
  }, []);

  return (
    <>
      <section className="space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300/80">Library</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Documents</h1>
            <p className="mt-2 text-sm text-zinc-400">{isDeletedView ? 'Recover or permanently remove deleted documents.' : selectedFolder ? `Files in ${selectedFolder.name}` : 'Choose a folder to browse your files.'}</p>
          </div>
          <div className="flex gap-2">
            <button type="button" className={`rounded-xl border px-4 py-2.5 text-sm font-medium ${isDeletedView ? 'border-amber-500/50 bg-amber-500/10 text-amber-300' : 'border-zinc-700 text-zinc-300'}`} onClick={() => setIsDeletedView((value) => !value)}>
              {isDeletedView ? 'Back to library' : 'Deleted'}
            </button>
            <button type="button" className="rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50" onClick={() => setIsUploadOpen(true)} disabled={!selectedFolder || isDeletedView}>
              Upload
            </button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
          <FolderSidebar selectedFolderId={selectedFolder?.id ?? null} onSelectFolder={handleSelectFolder} />
          <DocumentList folderId={selectedFolder?.id ?? null} isDeletedView={isDeletedView} />
        </div>
      </section>

      <UploadDialog
        folderId={selectedFolder?.id ?? null}
        folderName={selectedFolder?.name ?? 'the selected folder'}
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
      />
    </>
  );
}
