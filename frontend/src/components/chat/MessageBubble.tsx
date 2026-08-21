import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import type { ChatMessage } from '../../types/chat';

export function MessageBubble({ message }: { message: ChatMessage }) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${isUser ? 'bg-emerald-500 text-zinc-950' : 'border border-zinc-800 bg-zinc-900 text-zinc-100'}`}>
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none leading-6">
            <ReactMarkdown
              components={{
                h1: ({ children }) => <h1 className="mb-3 mt-4 text-xl font-bold first:mt-0">{children}</h1>,
                h2: ({ children }) => <h2 className="mb-2 mt-4 text-lg font-semibold first:mt-0">{children}</h2>,
                h3: ({ children }) => <h3 className="mb-2 mt-3 text-base font-semibold first:mt-0">{children}</h3>,
                p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
                ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
                li: ({ children }) => <li>{children}</li>,
                strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                em: ({ children }) => <em className="italic">{children}</em>,
                code({ className, children, ...props }) {
                  const language = /language-(\w+)/.exec(className ?? '')?.[1];
                  return language ? (
                    <SyntaxHighlighter
                      style={oneDark}
                      language={language}
                      PreTag="div"
                      className="!my-3 rounded-lg text-xs"
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
        {!isUser && message.citations?.length ? (
          <div className="mt-3 border-t border-zinc-700 pt-2">
            <button type="button" className="text-xs font-medium text-emerald-300" onClick={() => setShowSources((value) => !value)}>
              {showSources ? 'Hide sources' : `Sources (${message.citations.length})`}
            </button>
            {showSources ? (
              <div className="mt-2 space-y-2">
                {message.citations.map((citation) => (
                  <details key={citation.chunk_id} className="rounded-lg bg-zinc-950/70 p-2 text-xs text-zinc-300">
                    <summary className="cursor-pointer">
                      Document {citation.document_id.slice(0, 8)} · chunk {citation.chunk_index} · {(citation.similarity_score * 100).toFixed(1)}%
                    </summary>
                    <p className="mt-2 line-clamp-4 text-zinc-400">{citation.chunk_text}</p>
                  </details>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
