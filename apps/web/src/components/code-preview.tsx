"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const RAW_BASE = "https://raw.githubusercontent.com";

type Props = {
  repoTemplateUrl: string | null;
  branch: string | null;
  paths: string[];
};

function parseOwnerRepo(url: string): { owner: string; repo: string } | null {
  try {
    const u = new URL(url);
    if (u.hostname !== "github.com") return null;
    const [, owner, repo] = u.pathname.split("/");
    if (!owner || !repo) return null;
    return { owner, repo: repo.replace(/\.git$/, "") };
  } catch {
    return null;
  }
}

function languageFromPath(path: string): string {
  if (path.endsWith(".py")) return "python";
  if (path.endsWith(".ts") || path.endsWith(".tsx")) return "ts";
  if (path.endsWith(".js") || path.endsWith(".jsx")) return "js";
  if (path.endsWith(".md")) return "md";
  if (path.endsWith(".yml") || path.endsWith(".yaml")) return "yaml";
  if (path.endsWith(".toml")) return "toml";
  if (path.endsWith(".json")) return "json";
  return "txt";
}

export function CodePreview({ repoTemplateUrl, branch, paths }: Props) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [contents, setContents] = useState<Record<string, string | { error: string }>>({});

  const meta = repoTemplateUrl ? parseOwnerRepo(repoTemplateUrl) : null;
  const ref = branch || "main";

  useEffect(() => {
    if (!meta || paths.length === 0) return;
    const activePath = paths[activeIdx];
    if (activePath in contents) return;

    let cancelled = false;
    (async () => {
      const url = `${RAW_BASE}/${meta.owner}/${meta.repo}/${ref}/${activePath}`;
      try {
        const res = await fetch(url, { cache: "no-cache" });
        if (cancelled) return;
        if (!res.ok) {
          setContents((c) => ({ ...c, [activePath]: { error: `${res.status}` } }));
          return;
        }
        const text = await res.text();
        setContents((c) => ({ ...c, [activePath]: text }));
      } catch (exc) {
        if (cancelled) return;
        setContents((c) => ({
          ...c,
          [activePath]: { error: exc instanceof Error ? exc.message : "fetch failed" },
        }));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [meta, ref, paths, activeIdx, contents]);

  if (!meta) {
    return (
      <p className="text-sm text-muted-foreground">
        No template repo configured for this challenge.
      </p>
    );
  }
  if (paths.length === 0) return null;

  const activePath = paths[activeIdx];
  const body = contents[activePath];

  return (
    <section className="space-y-3">
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Files</h2>
        <a
          href={`${repoTemplateUrl}/tree/${ref}`}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-blue-600 hover:underline"
        >
          Open on GitHub →
        </a>
      </header>

      <div className="flex flex-wrap gap-1 overflow-x-auto border-b border-border">
        {paths.map((p, i) => (
          <button
            key={p}
            type="button"
            onClick={() => setActiveIdx(i)}
            className={cn(
              "rounded-t-md border-b-2 px-3 py-1.5 font-mono text-xs",
              i === activeIdx
                ? "border-primary bg-muted text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="rounded-md border border-border bg-muted/20">
        <div className="flex items-center justify-between border-b border-border px-3 py-1.5 text-xs text-muted-foreground">
          <span className="font-mono">{activePath}</span>
          <span>
            {languageFromPath(activePath)} · branch <code className="font-mono">{ref}</code>
          </span>
        </div>
        {body === undefined ? (
          <p className="px-3 py-6 text-center text-xs text-muted-foreground">Loading…</p>
        ) : typeof body === "object" ? (
          <p className="px-3 py-6 text-center text-xs text-red-600">
            Could not load file ({body.error}).
          </p>
        ) : (
          <pre className="max-h-[480px] overflow-auto px-3 py-3 text-xs leading-relaxed">
            <code className="font-mono">{body}</code>
          </pre>
        )}
      </div>
    </section>
  );
}
