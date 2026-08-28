import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listNotes, createNote, deleteNote, notesQueryKey } from '../services/notes';
import type { Note } from '../types/notes';

export function Notes() {
  const qc = useQueryClient();
  const { data: notes = [], isLoading, isError, error } = useQuery({ queryKey: notesQueryKey, queryFn: listNotes });
  const [isCreating, setIsCreating] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const createMutation = useMutation({ mutationFn: ({ title, content }: { title: string; content: string }) => createNote(title, content), onSuccess: () => { setIsCreating(false); setTitle(''); setContent(''); setFormError(null); void qc.invalidateQueries({ queryKey: notesQueryKey }); } });
  const deleteMutation = useMutation({ mutationFn: (id: string) => deleteNote(id), onSuccess: () => void qc.invalidateQueries({ queryKey: notesQueryKey }) });

  if (isLoading) return <div className="animate-pulse">Loading notes...</div>;
  if (isError) return <div className="text-rose-300">Failed to load notes: {(error as any)?.message ?? 'Unknown'}</div>;

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300/80">Notes</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Quick Notes</h1>
          <p className="mt-2 text-sm text-zinc-400">Create quick plain-text notes for capture and reference.</p>
        </div>
        <div>
          {!isCreating ? (
            <button type="button" className="rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-zinc-950" onClick={() => setIsCreating(true)}>New Note</button>
          ) : (
            <div className="space-y-2">
              <input className="w-96 rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
              <textarea className="w-96 h-40 rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" placeholder="Content" value={content} onChange={(e) => setContent(e.target.value)} />
              <div className="flex gap-2">
                <button type="button" className="rounded-xl bg-emerald-500 px-3 py-1 text-sm font-medium text-zinc-950" onClick={() => { const t = title.trim(); const c = content.trim(); if (!t) { setFormError('Title is required'); return; } setFormError(null); createMutation.mutate({ title: t, content: c }); }} disabled={createMutation.isPending}>Create</button>
                <button type="button" className="rounded-xl border border-zinc-700 px-3 py-1 text-sm text-zinc-300" onClick={() => { setIsCreating(false); setTitle(''); setContent(''); setFormError(null); }}>Cancel</button>
              </div>
              {formError ? <div className="text-sm text-rose-300">{formError}</div> : null}
            </div>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {notes.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-zinc-800 p-6 text-center text-sm text-zinc-400">No notes yet. Create one to get started.</div>
        ) : (
          notes.map((note: Note) => (
            <div key={note.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-medium text-zinc-100">{note.title}</h3>
                  <p className="mt-1 text-xs text-zinc-400">{new Date(note.created_at).toLocaleString()}</p>
                  <p className="mt-2 text-sm text-zinc-300">{note.content.length > 200 ? note.content.slice(0, 200) + '…' : note.content}</p>
                </div>
                <div className="flex flex-col gap-2">
                  <button type="button" className="rounded-lg border border-rose-800 px-3 py-1.5 text-xs text-rose-300" onClick={() => { if (!confirm('Delete this note?')) return; deleteMutation.mutate(note.id); }} disabled={deleteMutation.isPending}>Delete</button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
