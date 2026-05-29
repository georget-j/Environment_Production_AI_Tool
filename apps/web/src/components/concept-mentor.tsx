"use client";

/**
 * Concept-mode mentor panel (M1).
 *
 * Slim chat UI for asking Socratic teaching questions about the concept
 * the learner is currently studying. Distinct from the challenge-mode
 * mentor (Hint 1/2/3 + Show Answer) — concept-mode is just question →
 * answer, no escalation levels, no show-answer escape hatch.
 *
 * Layout:
 *   - lg+: right-rail panel (parent provides the column)
 *   - md and below: collapsed by default; expanded as a slide-up sheet
 *
 * The panel holds its own conversation history client-side; every API
 * call ships the full history so the server is stateless. (Same shape
 * as the challenge-mode mentor in mentor-chat.tsx, but no persistence —
 * concept mentor turns are ephemeral.)
 */

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import { type ConceptMentorTurn, askConceptMentor } from "@/lib/concepts";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

const STARTER_PROMPTS = [
  "Why does this work that way?",
  "Can you walk me through the worked example?",
  "What's an example where this breaks?",
];

export function ConceptMentor({
  conceptSlug,
  stage,
}: {
  conceptSlug: string;
  stage?: string;
}) {
  const [turns, setTurns] = useState<ConceptMentorTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  // Reset the transcript when the learner moves to a different concept.
  // Stages don't reset — questions across stages of the same concept
  // share context.
  useEffect(() => {
    setTurns([]);
    setDraft("");
    setError(null);
  }, [conceptSlug]);

  useEffect(() => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
    }
  }, [turns, pending]);

  async function send(text: string) {
    if (!text.trim() || pending) return;
    setPending(true);
    setError(null);
    const userTurn: ConceptMentorTurn = { role: "user", content: text };
    const nextTurns = [...turns, userTurn];
    setTurns(nextTurns);
    setDraft("");
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) {
        setTurns([
          ...nextTurns,
          {
            role: "assistant",
            content:
              "You need to be signed in to use the mentor. Refresh after signing in.",
          },
        ]);
        return;
      }
      const res = await askConceptMentor(
        token,
        conceptSlug,
        text,
        turns, // history WITHOUT the just-added user turn (server appends it)
        stage,
      );
      setTurns([...nextTurns, { role: "assistant", content: res.reply }]);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Mentor call failed.");
      // Roll back the optimistic user turn so the learner can retry.
      setTurns(turns);
    } finally {
      setPending(false);
    }
  }

  return (
    <aside className="flex flex-col gap-3 rounded-lg border border-border bg-background">
      <header className="border-b border-border px-3 py-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Mentor
        </p>
        <p className="text-sm font-medium">Ask anything about this concept</p>
      </header>

      <div
        ref={scrollerRef}
        className="flex max-h-[60vh] min-h-[160px] flex-col gap-2 overflow-y-auto px-3 pb-2"
      >
        {turns.length === 0 && !pending && (
          <div className="flex flex-col gap-2 text-xs">
            <p className="text-muted-foreground">
              I&apos;m here to teach the concept, not the task. Try one of these
              — or ask your own.
            </p>
            <div className="flex flex-col gap-1">
              {STARTER_PROMPTS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => send(p)}
                  className="rounded-md border border-border bg-muted/30 px-2 py-1.5 text-left text-xs hover:bg-muted/60"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t, i) => (
          <div
            key={i}
            className={
              t.role === "user"
                ? "self-end max-w-[90%] rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground"
                : "self-start max-w-[95%] rounded-md border border-border bg-muted/30 px-3 py-2 text-sm"
            }
          >
            {t.role === "assistant" ? (
              <div className="prose prose-sm max-w-none prose-p:my-1 prose-code:rounded prose-code:bg-background prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:text-[0.85em] prose-code:before:content-none prose-code:after:content-none">
                <ReactMarkdown>{t.content}</ReactMarkdown>
              </div>
            ) : (
              <p className="whitespace-pre-wrap">{t.content}</p>
            )}
          </div>
        ))}
        {pending && (
          <p className="self-start rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            Thinking…
          </p>
        )}
      </div>

      {error && <p className="px-3 text-xs text-red-700">{error}</p>}

      <form
        className="flex items-end gap-2 border-t border-border p-2"
        onSubmit={(e) => {
          e.preventDefault();
          void send(draft);
        }}
      >
        <textarea
          rows={2}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(draft);
            }
          }}
          placeholder="Ask the mentor (Enter to send, Shift+Enter for newline)"
          className="flex-1 resize-none rounded-md border border-border bg-background p-2 text-sm focus:border-foreground focus:outline-none"
          disabled={pending}
        />
        <Button type="submit" size="sm" disabled={pending || !draft.trim()}>
          Ask
        </Button>
      </form>
    </aside>
  );
}
