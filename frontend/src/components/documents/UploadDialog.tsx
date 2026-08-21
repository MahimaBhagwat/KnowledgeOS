import { useRef, useState, useEffect, type ChangeEvent, type DragEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  documentsQueryKey,
  foldersQueryKey,
  uploadDocument,
  getFolders,
} from '../../services/documentLibrary';
import type { FolderItem } from '../../types/documents';

interface UploadDialogProps {
  folderId: string | null;
  folderName: string;
  isOpen: boolean;
  onClose: () => void;
}

export function UploadDialog({ folderId, folderName, isOpen, onClose }: UploadDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [selectedFolderIdLocal, setSelectedFolderIdLocal] = useState<string | null>(folderId);

  const foldersQuery = useQuery({ queryKey: foldersQueryKey, queryFn: getFolders });

  // keep local selected folder in sync when dialog opens or folderId prop changes
  useEffect(() => {
    if (isOpen) {
      const uploadedFolder = foldersQuery.data?.find((f) => f.folder_type === 'uploaded');
      setSelectedFolderIdLocal(uploadedFolder?.id ?? folderId);
    }
  }, [isOpen, folderId, foldersQuery.data]);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const targetFolderId = selectedFolderIdLocal ?? folderId;
      if (!targetFolderId) {
        throw new Error('Select a folder before uploading.');
      }
      return uploadDocument(file, targetFolderId, setProgress);
    },
    onSuccess: () => {
      const target = selectedFolderIdLocal ?? folderId;
      if (target) {
        void queryClient.invalidateQueries({ queryKey: documentsQueryKey(target) });
      }
      void queryClient.invalidateQueries({ queryKey: foldersQueryKey });
    },
  });

  if (!isOpen) {
    return null;
  }

  const selectFile = (file: File | undefined): void => {
    if (!file) {
      return;
    }
    setProgress(0);
    uploadMutation.reset();
    uploadMutation.mutate(file);
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>): void => {
    selectFile(event.target.files?.[0]);
    event.target.value = '';
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>): void => {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files[0]);
  };

  const selectedFolderName = foldersQuery.data?.find((f) => f.id === selectedFolderIdLocal)?.name ?? folderName;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-lg rounded-3xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Upload document</h2>
            <p className="mt-1 text-sm text-zinc-400">Add a file to {selectedFolderName}.</p>
          <div className="mt-3">
            <label className="mb-1 block text-xs text-zinc-400">Upload target folder</label>
            <select
              className="w-full rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              value={selectedFolderIdLocal ?? ''}
              onChange={(e) => setSelectedFolderIdLocal(e.target.value || null)}
            >
              {foldersQuery.data?.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>
          </div>
          <button type="button" className="text-zinc-400 hover:text-white" onClick={onClose} aria-label="Close upload dialog">
            ×
          </button>
        </div>

        <div
          className={`mt-6 rounded-2xl border-2 border-dashed p-10 text-center transition ${
            isDragging ? 'border-emerald-400 bg-emerald-500/10' : 'border-zinc-700 bg-zinc-950/50'
          }`}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <p className="text-sm text-zinc-300">Drag and drop a file here</p>
          <p className="my-2 text-xs text-zinc-500">or</p>
          <button
            type="button"
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-emerald-400"
            onClick={() => inputRef.current?.click()}
            disabled={uploadMutation.isPending}
          >
            Browse files
          </button>
          <input ref={inputRef} className="hidden" type="file" onChange={handleInputChange} />
        </div>

        {uploadMutation.isPending ? (
          <div className="mt-5">
            <div className="mb-2 flex justify-between text-xs text-zinc-400">
              <span>Uploading...</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
              <div className="h-full rounded-full bg-emerald-400 transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
        ) : null}

        {uploadMutation.isSuccess ? (
          <div className="mt-5 rounded-xl border border-emerald-900 bg-emerald-500/10 p-3 text-sm text-emerald-200">
            Upload complete.
          </div>
        ) : null}
        {uploadMutation.isError ? (
          <div className="mt-5 rounded-xl border border-rose-900 bg-rose-500/10 p-3 text-sm text-rose-200">
            Upload failed: {uploadMutation.error.message}
          </div>
        ) : null}

        <div className="mt-6 flex justify-end">
          <button type="button" className="rounded-xl border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:text-white" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
