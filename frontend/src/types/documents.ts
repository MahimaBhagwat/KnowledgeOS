export type FolderType = 'uploaded' | 'quick_notes' | 'archive' | 'custom';

export interface FolderItem {
  id: string;
  profile_id: string;
  name: string;
  folder_type: FolderType;
  is_system_folder: boolean;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  profile_id: string;
  folder_id: string;
  name: string;
  file_path: string;
  file_type: string;
  file_size: number;
  is_favorite: boolean;
  is_deleted: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}
