import { apiDelete, apiGet, apiPatch, apiPost, apiUpload } from './api';
import type { DocumentItem, FolderItem } from '../types/documents';

export const foldersQueryKey = ['folders'] as const;
export const documentsQueryKey = (folderId: string, isDeleted = false) => ['documents', folderId, { isDeleted }] as const;

export async function getFolders(): Promise<FolderItem[]> {
  return apiGet<FolderItem[]>('/folders/');
}

export async function getDocuments(folderId: string, options?: { isDeleted?: boolean; isFavorite?: boolean }): Promise<DocumentItem[]> {
  return apiGet<DocumentItem[]>('/documents/', {
    folder_id: folderId,
    is_deleted: options?.isDeleted ?? false,
    is_favorite: options?.isFavorite,
  });
}

export async function uploadDocument(file: File, folderId: string, onProgress: (progress: number) => void): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('folder_id', folderId);

  return apiUpload<DocumentItem>('/documents/upload', formData, {
    onUploadProgress: onProgress,
  });
}

export async function toggleFavorite(documentId: string, isFavorite: boolean): Promise<DocumentItem> {
  return apiPatch<DocumentItem>(`/documents/${documentId}`, { is_favorite: isFavorite });
}

export async function softDeleteDocument(documentId: string): Promise<DocumentItem> {
  return apiPost<DocumentItem>(`/documents/${documentId}/soft-delete`);
}

export async function restoreDocument(documentId: string): Promise<DocumentItem> {
  return apiPost<DocumentItem>(`/documents/${documentId}/restore`);
}

export async function renameDocument(documentId: string, name: string): Promise<DocumentItem> {
  return apiPatch<DocumentItem>(`/documents/${documentId}`, { name });
}

export async function permanentlyDeleteDocument(documentId: string): Promise<void> {
  await apiDelete<void>(`/documents/${documentId}`);
}

export interface DocumentInsights {
  document_id: string;
  summary: string;
  key_takeaways: string[];
  flashcards: { question: string; answer: string }[];
}

export async function generateDocumentInsights(documentId: string): Promise<DocumentInsights> {
  return apiPost<DocumentInsights>(`/insights/documents/${documentId}`);
}

export async function createFolder(name: string): Promise<FolderItem> {
  return apiPost<FolderItem>('/folders/', { name });
}

export async function renameFolder(folderId: string, name: string): Promise<FolderItem> {
  return apiPatch<FolderItem>(`/folders/${folderId}`, { name });
}
