import { readFile } from "node:fs/promises";
import { join } from "node:path";
import Link from "next/link";
import { Markdown } from "@/components/markdown";

export const dynamic = "force-static";

export default async function QuantRoadmapPage() {
  // Resolve relative to the repo root so this works in dev and on Vercel.
  // The file lives at <repo>/docs/quant-roadmap.md; cwd is apps/web at build/run time.
  const path = join(process.cwd(), "..", "..", "docs", "quant-roadmap.md");
  const source = await readFile(path, "utf-8");
  return (
    <div className="space-y-6 py-8">
      <header className="space-y-2">
        <Link
          href="/tracks/quant-programmer"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          ← Back to the Quant Programmer track
        </Link>
        <p className="text-xs uppercase tracking-wide text-muted-foreground">Roadmap</p>
      </header>
      <article className="prose-sm max-w-3xl">
        <Markdown>{source}</Markdown>
      </article>
    </div>
  );
}
