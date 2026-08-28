export interface Note {
  id: string;
  profile_id: string;
  title: string;
  content: string;
  folder_id: string | null;
  created_at: string;
}
