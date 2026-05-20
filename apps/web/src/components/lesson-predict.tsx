"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { PredictLessonConfig } from "@/lib/featured-files";

type Props = {
  config: PredictLessonConfig;
};

function normalise(s: string): string {
  return s.replace(/\s+$/g, "").trimStart();
}

export function LessonPredict({ config }: Props) {
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<"correct" | "wrong" | null>(null);
  const [revealed, setRevealed] = useState(false);

  function check(e: React.FormEvent) {
    e.preventDefault();
    if (normalise(answer) === normalise(config.expected_stdout)) {
      setResult("correct");
    } else {
      setResult("wrong");
    }
  }

  function tryAgain() {
    setResult(null);
    setRevealed(false);
  }

  return (
    <section className="flex h-full flex-col gap-4 rounded-lg border border-border bg-background p-4">
      <div>
        <h3 className="mb-2 text-sm font-semibold">Read this code</h3>
        <pre className="overflow-x-auto rounded-md border border-border bg-muted/30 p-3 font-mono text-xs leading-relaxed">
          <code>{config.code}</code>
        </pre>
      </div>

      <form onSubmit={check} className="space-y-2">
        <label className="block text-sm font-medium">
          {config.prompt ?? "What will this print?"}
        </label>
        <textarea
          rows={3}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type the exact output you expect…"
          disabled={result === "correct"}
          className="block w-full resize-none rounded-md border border-border bg-background px-3 py-2 font-mono text-xs leading-relaxed"
        />
        {result === null && (
          <Button type="submit" disabled={!answer.trim()} className="w-full">
            Check
          </Button>
        )}
      </form>

      {result === "correct" && (
        <div className="rounded-md border border-green-300 bg-green-50 px-3 py-2 text-sm text-green-800">
          ✓ Correct. Use the lesson navigation to move on.
        </div>
      )}

      {result === "wrong" && (
        <div className="space-y-2 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          <p>Not quite. Re-read the code and try again — pay attention to spacing and casing.</p>
          {revealed ? (
            <pre className="overflow-x-auto rounded border border-red-200 bg-white p-2 font-mono text-xs text-red-900">
              <code>{config.expected_stdout}</code>
            </pre>
          ) : (
            <button
              type="button"
              onClick={() => setRevealed(true)}
              className="text-xs underline hover:no-underline"
            >
              Show the expected output
            </button>
          )}
          <div className="flex justify-end">
            <Button type="button" size="sm" variant="outline" onClick={tryAgain}>
              Try again
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
