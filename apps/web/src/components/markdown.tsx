"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-sm max-w-none text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="mb-3 mt-6 text-xl font-semibold" {...p} />,
          h2: (p) => <h2 className="mb-2 mt-5 text-lg font-semibold" {...p} />,
          h3: (p) => <h3 className="mb-2 mt-4 text-base font-semibold" {...p} />,
          p: (p) => <p className="mb-3" {...p} />,
          ul: (p) => <ul className="mb-3 list-disc space-y-1 pl-5" {...p} />,
          ol: (p) => <ol className="mb-3 list-decimal space-y-1 pl-5" {...p} />,
          li: (p) => <li {...p} />,
          a: ({ href, ...rest }) => (
            <a
              href={href}
              className="text-blue-600 hover:underline"
              target={href?.startsWith("http") ? "_blank" : undefined}
              rel={href?.startsWith("http") ? "noreferrer" : undefined}
              {...rest}
            />
          ),
          code: ({ className, children, ...rest }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code
                  className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs"
                  {...rest}
                >
                  {children}
                </code>
              );
            }
            return (
              <code className={`font-mono text-xs ${className ?? ""}`} {...rest}>
                {children}
              </code>
            );
          },
          pre: (p) => (
            <pre
              className="my-3 overflow-x-auto rounded-md border border-border bg-muted/30 p-3"
              {...p}
            />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
