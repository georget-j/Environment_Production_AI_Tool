"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Glossary } from "@/components/glossary";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Turn = {
  id: string;
  role: "user" | "assistant";
  content: string;
  hint_level: number | null;
  created_at: string;
};

/** Imperative surface that parents can call into. The Stuck? button on the
 * challenge runner uses this to ask a question on the learner's behalf. */
export type MentorChatHandle = {
  askMentor: (message: string, hintLevel?: 1 | 2 | 3) => Promise<void>;
  scrollIntoView: () => void;
};

export const MentorChat = forwardRef<MentorChatHandle, { challengeId: string }>(function MentorChat(
  { challengeId },
  ref,
) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [message, setMessage] = useState("");
  const [hintLevel, setHintLevel] = useState<1 | 2 | 3>(1);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement | null>(null);
  const rootRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    (async () => {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) return;
      const res = await fetch(`${API_BASE_URL}/api/ai/messages/${challengeId}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
        cache: "no-store",
      });
      if (res.ok) setTurns(await res.json());
    })();
  }, [challengeId]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns.length]);

  async function postChat(text: string, level: 1 | 2 | 3): Promise<boolean> {
    setPending(true);
    setError(null);
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      setPending(false);
      setError("Sign in to chat with the mentor.");
      return false;
    }
    const response = await fetch(`${API_BASE_URL}/api/ai/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ challenge_id: challengeId, message: text, hint_level: level }),
    });

    setPending(false);
    if (!response.ok) {
      const body = await response.text();
      setError(`Chat failed (${response.status}): ${body.slice(0, 200)}`);
      return false;
    }
    const data = await response.json();
    setTurns((prev) => [...prev, data.user_turn, data.assistant_turn]);
    return true;
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    const ok = await postChat(message, hintLevel);
    if (ok) setMessage("");
  }

  // Imperative API for parents (Stuck? button on the challenge runner).
  useImperativeHandle(
    ref,
    () => ({
      async askMentor(text: string, level: 1 | 2 | 3 = 2) {
        setHintLevel(level);
        rootRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        await postChat(text, level);
      },
      scrollIntoView() {
        rootRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      },
    }),
    // postChat captures challengeId via closure; explicit dep keeps lint happy.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [challengeId],
  );

  async function clear() {
    if (turns.length === 0) return;
    if (!confirm("Clear the entire mentor conversation for this challenge?")) return;
    setError(null);
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      setError("Sign in to clear the chat.");
      return;
    }
    const response = await fetch(`${API_BASE_URL}/api/ai/messages/${challengeId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${session.access_token}` },
    });
    if (!response.ok) {
      const body = await response.text();
      setError(`Clear failed (${response.status}): ${body.slice(0, 200)}`);
      return;
    }
    setTurns([]);
  }

  return (
    <section ref={rootRef} className="rounded-lg border border-border">
      <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold">AI mentor</h3>
        <div className="flex items-center gap-2 text-xs">
          {[1, 2, 3].map((level) => (
            <button
              key={level}
              type="button"
              onClick={() => setHintLevel(level as 1 | 2 | 3)}
              className={`rounded-md px-2 py-1 ${
                hintLevel === level
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted"
              }`}
            >
              Hint {level}
            </button>
          ))}
          <button
            type="button"
            onClick={clear}
            disabled={turns.length === 0}
            className="rounded-md px-2 py-1 text-muted-foreground hover:bg-muted disabled:opacity-40"
            title="Delete all mentor messages for this challenge"
          >
            Clear
          </button>
        </div>
      </header>

      <div ref={scroller} className="max-h-96 space-y-3 overflow-y-auto p-4 text-sm">
        {turns.length === 0 ? (
          <p className="text-muted-foreground">
            Ask a question. <Glossary term="hint">Hint 1 is Socratic — it asks you a question
            instead of giving an answer. Hint 3 sketches pseudocode.</Glossary>
          </p>
        ) : (
          turns.map((t) => (
            <div
              key={t.id}
              className={`rounded-md px-3 py-2 ${
                t.role === "user" ? "bg-muted/40" : "bg-background border border-border"
              }`}
            >
              <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
                {t.role}
                {t.hint_level !== null && ` · hint ${t.hint_level}`}
              </p>
              <p className="whitespace-pre-wrap">{t.content}</p>
            </div>
          ))
        )}
      </div>

      <form onSubmit={send} className="space-y-2 border-t border-border p-4">
        <textarea
          rows={2}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="What's confusing you right now?"
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
        <Button type="submit" disabled={pending || !message.trim()} className="w-full">
          {pending ? "Thinking…" : "Ask"}
        </Button>
      </form>
    </section>
  );
});
