"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { celebrate } from "@/lib/celebrate";
import type { PredictLessonConfig } from "@/lib/featured-files";

type Props = {
  config: PredictLessonConfig;
  nextSlug: string | null;
};

const AUTO_ADVANCE_MS = 1500;

function normalise(s: string): string {
  return s.replace(/\s+$/g, "").trimStart();
}

export function LessonPredict({ config, nextSlug }: Props) {
  const router = useRouter();
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<"correct" | "wrong" | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [autoCancelled, setAutoCancelled] = useState(false);
  const successCardRef = useRef<HTMLDivElement | null>(null);

  // Fire confetti once when the user gets it right.
  useEffect(() => {
    if (result === "correct") void celebrate();
  }, [result]);

  // Auto-advance unless the user moves a pointer over the success card.
  useEffect(() => {
    if (result !== "correct" || !nextSlug || autoCancelled) return;
    const id = window.setTimeout(
      () => router.push(`/challenges/${nextSlug}`),
      AUTO_ADVANCE_MS,
    );
    return () => window.clearTimeout(id);
  }, [result, nextSlug, autoCancelled, router]);

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
    <section className="flex flex-col gap-4 rounded-lg border border-border bg-background p-4">
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
        <div
          ref={successCardRef}
          onPointerEnter={() => setAutoCancelled(true)}
          onFocusCapture={() => setAutoCancelled(true)}
          className="space-y-3 rounded-md border border-green-300 bg-green-50 px-4 py-3"
        >
          <p className="text-sm font-semibold text-green-900">
            ✓ Correct! Nice work.
          </p>
          {nextSlug ? (
            <>
              <Button
                type="button"
                className="w-full"
                onClick={() => router.push(`/challenges/${nextSlug}`)}
              >
                Next lesson →
              </Button>
              {!autoCancelled ? (
                <p className="text-center text-[11px] text-green-900/70">
                  Auto-advancing in {Math.round(AUTO_ADVANCE_MS / 1000)}s …{" "}
                  <button
                    type="button"
                    onClick={() => setAutoCancelled(true)}
                    className="underline hover:no-underline"
                  >
                    Stay on this lesson
                  </button>
                </p>
              ) : (
                <p className="text-center text-[11px] text-green-900/70">
                  Take your time — click Next when you&apos;re ready.
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-green-900">
              You&apos;ve finished the last lesson of this track 🎉
            </p>
          )}
        </div>
      )}

      {result === "wrong" && (
        <div className="space-y-2 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          <p>
            Not quite. Re-read the code and try again — pay attention to spacing
            and casing.
          </p>
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
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={tryAgain}
            >
              Try again
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
