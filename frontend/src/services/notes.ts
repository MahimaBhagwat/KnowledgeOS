import { apiGet, apiPost, apiDelete } from './api';
import type { Note } from '../types/notes';

export const notesQueryKey = ['notes'] as const;

export async function listNotes(): Promise<Note[]> {
  return apiGet<Note[]>('/notes/');
}

export async function createNote(title: string, content: string, folderId?: string | null): Promise<Note> {
  const body: Record<string, unknown> = { title, content };
  if (folderId) body.folder_id = folderId;
  return apiPost<Note>('/notes/', body);
}

export async function deleteNote(id: string): Promise<void> {
  await apiDelete<void>(`/notes/${id}`);
}
