import { useState, useEffect } from 'react';
import { Sliders, Sparkles, Check, Key, Palette } from 'lucide-react';
import { applyTheme, getInitialTheme, type Theme } from '../utils/theme';

export function Settings() {
  const [theme, setThemeState] = useState<Theme>(() => getInitialTheme());
  const [streamingEnabled, setStreamingEnabled] = useState(() => localStorage.getItem('ko_streaming') !== 'false');
  const [agenticEnabled, setAgenticEnabled] = useState(() => localStorage.getItem('ko_agentic') !== 'false');
  const [retrievalTopK, setRetrievalTopK] = useState(() => Number(localStorage.getItem('ko_top_k')) || 5);
  const [customApiKey, setCustomApiKey] = useState(() => localStorage.getItem('ko_custom_api_key') || '');
  const [savedMessage, setSavedMessage] = useState(false);

  const handleThemeSelect = (newTheme: Theme) => {
    setThemeState(newTheme);
    applyTheme(newTheme);
  };

  useEffect(() => {
    localStorage.setItem('ko_streaming', String(streamingEnabled));
    localStorage.setItem('ko_agentic', String(agenticEnabled));
    localStorage.setItem('ko_top_k', String(retrievalTopK));
    localStorage.setItem('ko_custom_api_key', customApiKey);
  }, [streamingEnabled, agenticEnabled, retrievalTopK, customApiKey]);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    applyTheme(theme);
    setSavedMessage(true);
    setTimeout(() => setSavedMessage(false), 2500);
  };

  return (
    <section className="space-y-6" aria-label="System Settings">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300/80">Preferences</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">System Settings</h1>
        <p className="mt-2 text-sm text-zinc-400">Configure your AI pipeline, retrieval parameters, and UI theme.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-6 max-w-2xl">
        {/* UI Theme */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-6" role="region" aria-label="Interface Theme Settings">
          <div className="flex items-center gap-2 mb-1">
            <Palette className="h-4 w-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-zinc-200">Interface Theme</h2>
          </div>
          <p className="text-xs text-zinc-400">Customize the appearance and color palette of your workspace.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            {[
              { id: 'dark', label: 'Dark Zinc' },
              { id: 'obsidian', label: 'Obsidian Black' },
              { id: 'midnight', label: 'Midnight Blue' },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => handleThemeSelect(t.id as Theme)}
                className={`rounded-xl border px-4 py-2.5 text-sm font-medium transition focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:outline-none ${
                  theme === t.id
                    ? 'border-emerald-500 bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/30'
                    : 'border-zinc-700 bg-zinc-900 text-zinc-300 hover:border-zinc-500'
                }`}
                aria-pressed={theme === t.id}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* AI & RAG Configuration */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-6 space-y-4" role="region" aria-label="AI Pipeline Settings">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="h-4 w-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-zinc-200">AI & RAG Pipeline</h2>
          </div>
          <p className="text-xs text-zinc-400">Control generative streaming, agentic stages, and context retrieval depth.</p>

          <div className="flex items-center justify-between py-2.5 border-b border-zinc-800/80">
            <div>
              <div className="text-sm font-medium text-zinc-200">Stream Token Responses</div>
              <div className="text-xs text-zinc-500">Yield SSE tokens incrementally as the LLM generates them.</div>
            </div>
            <input
              type="checkbox"
              checked={streamingEnabled}
              onChange={(e) => setStreamingEnabled(e.target.checked)}
              className="h-5 w-5 rounded border-zinc-700 bg-zinc-900 text-emerald-500 focus:ring-emerald-400 cursor-pointer"
              aria-label="Toggle token streaming"
            />
          </div>

          <div className="flex items-center justify-between py-2.5 border-b border-zinc-800/80">
            <div>
              <div className="text-sm font-medium text-zinc-200">Agentic Multi-Stage Pipeline</div>
              <div className="text-xs text-zinc-500">Enable Planner → Executor → Reviewer multi-agent reasoning.</div>
            </div>
            <input
              type="checkbox"
              checked={agenticEnabled}
              onChange={(e) => setAgenticEnabled(e.target.checked)}
              className="h-5 w-5 rounded border-zinc-700 bg-zinc-900 text-emerald-500 focus:ring-emerald-400 cursor-pointer"
              aria-label="Toggle agentic pipeline"
            />
          </div>

          <div className="py-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-sm font-medium text-zinc-200">
                <Sliders className="h-3.5 w-3.5 text-zinc-400" />
                <span>Retrieval Depth (Top-K Chunks)</span>
              </div>
              <span className="text-sm font-bold text-emerald-300">{retrievalTopK} chunks</span>
            </div>
            <input
              type="range"
              min={1}
              max={15}
              value={retrievalTopK}
              onChange={(e) => setRetrievalTopK(Number(e.target.value))}
              className="mt-2.5 w-full accent-emerald-500 cursor-pointer"
              aria-label="Retrieval depth top-k slider"
            />
            <p className="mt-1 text-xs text-zinc-500">Higher numbers retrieve more context but consume more prompt tokens.</p>
          </div>
        </div>

        {/* Custom API Key */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-6 space-y-3" role="region" aria-label="API Key Settings">
          <div className="flex items-center gap-2 mb-1">
            <Key className="h-4 w-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-zinc-200">Custom Provider Key (Optional)</h2>
          </div>
          <p className="text-xs text-zinc-400">
            If provided, client-initiated tasks will prioritize this key over backend environment defaults (BYOK).
          </p>
          <input
            type="password"
            placeholder="sk-..."
            value={customApiKey}
            onChange={(e) => setCustomApiKey(e.target.value)}
            className="w-full rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus-visible:border-emerald-400 focus-visible:ring-2 focus-visible:ring-emerald-400"
            aria-label="Custom provider API key"
          />
        </div>

        {savedMessage && (
          <div className="flex items-center gap-2 rounded-xl border border-emerald-900 bg-emerald-500/10 p-3 text-sm text-emerald-200" role="status">
            <Check className="h-4 w-4 text-emerald-400" />
            <span>Settings saved successfully to local preferences.</span>
          </div>
        )}

        <button
          type="submit"
          className="flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-emerald-400 focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:outline-none"
        >
          <Check className="h-4 w-4" />
          <span>Save Changes</span>
        </button>
      </form>
    </section>
  );
}
