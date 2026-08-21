import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { generateDocumentInsights } from '../../services/documentLibrary';
import type { DocumentInsights as InsightsType } from '../../types/insights';

export default function InsightsPanel({ documentId, onClose }: { documentId: string | null; onClose: () => void }) {
  const { data, isLoading, isError, refetch } = useQuery<InsightsType>({ queryKey: ['document-insights', documentId], queryFn: () => generateDocumentInsights(documentId as string), enabled: Boolean(documentId) });
  const [revealedIndexes, setRevealedIndexes] = useState<Record<number, boolean>>({});

  if (!documentId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative mx-4 mb-6 w-full max-w-3xl rounded-2xl bg-zinc-950 p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Document Insights</h2>
          <div className="flex items-center gap-2">
            <button onClick={() => refetch()} className="rounded-md bg-zinc-800 px-3 py-1 text-xs text-zinc-200">Retry</button>
            <button onClick={onClose} className="rounded-md bg-zinc-700 px-3 py-1 text-xs text-zinc-200">Close</button>
          </div>
        </div>

        <div className="mt-4 max-h-[60vh] overflow-y-auto space-y-4">
          {isLoading ? (
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 text-sm text-zinc-400">Generating insights — this may take a few seconds...</div>
          ) : isError ? (
            <div className="rounded-lg border border-rose-800 bg-rose-500/10 p-4 text-sm text-rose-200">Failed to generate insights. Try again.</div>
          ) : data ? (
            <div className="space-y-4 text-sm text-zinc-200">
              <p className="text-zinc-300">{data.summary}</p>
              <div>
                <h3 className="mt-2 mb-1 font-medium">Key takeaways</h3>
                <ul className="ml-4 list-disc space-y-1 text-zinc-300">
                  {data.key_takeaways.map((k: string, i: number) => (
                    <li key={i}>{k}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h3 className="mt-3 mb-2 font-medium">Flashcards</h3>
                <div className="space-y-2">
                  {data.flashcards.map((f: { question: string; answer: string }, idx: number) => (
                    <div key={idx} className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-3">
                      <button
                        type="button"
                        className="w-full text-left text-sm font-medium text-zinc-100"
                        onClick={() => setRevealedIndexes((s) => ({ ...s, [idx]: !s[idx] }))}
                      >
                        <div className="flex flex-col items-start">
                          <span>{f.question}</span>
                          {revealedIndexes[idx] ? (
                            <p className="mt-2 text-sm text-zinc-300">{f.answer}</p>
                          ) : (
                            <p className="mt-2 text-sm text-zinc-500">(Click to reveal answer)</p>
                          )}
                        </div>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
