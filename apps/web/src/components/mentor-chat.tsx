"use client";

import { useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Turn = {
  id: string;
  role: "user" | "assistant";
  content: string;
  hint_level: number | null;
  created_at: string;
};

export function MentorChat({ challengeId }: { challengeId: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [message, setMessage] = useState("");
  const [hintLevel, setHintLevel] = useState<1 | 2 | 3>(1);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement | null>(null);

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

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setPending(true);
    setError(null);

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      setPending(false);
      setError("Sign in to chat with the mentor.");
      return;
    }
    const response = await fetch(`${API_BASE_URL}/api/ai/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ challenge_id: challengeId, message, hint_level: hintLevel }),
    });

    setPending(false);
    if (!response.ok) {
      const body = await response.text();
      setError(`Chat failed (${response.status}): ${body.slice(0, 200)}`);
      return;
    }
    const data = await response.json();
    setTurns((prev) => [...prev, data.user_turn, data.assistant_turn]);
    setMessage("");
  }

  return (
    <section className="rounded-lg border border-border">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold">AI mentor</h3>
        <div className="flex items-center gap-1 text-xs">
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
        </div>
      </header>

      <div ref={scroller} className="max-h-96 space-y-3 overflow-y-auto p-4 text-sm">
        {turns.length === 0 ? (
          <p className="text-muted-foreground">
            Ask a question. Hint 1 is Socratic; Hint 3 sketches pseudocode.
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
}
