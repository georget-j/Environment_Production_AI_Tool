"use client";

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { Glossary } from "@/components/glossary";
import { MentorMessage } from "@/components/mentor-message";
import { cn } from "@/lib/utils";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Turn = {
  id: string;
  role: "user" | "assistant";
  content: string;
  hint_level: number | null;
  created_at: string;
};

export type MentorChatHandle = {
  askMentor: (message: string, hintLevel?: 1 | 2 | 3) => Promise<void>;
  scrollIntoView: () => void;
  /** Append a client-side-only assistant message (e.g. show-answer summary).
   * Not persisted to the AIMessage table. */
  appendAssistantNotice: (text: string) => void;
};

type Props = {
  challengeId: string;
  onJumpToCode?: (file: string, line: number | null) => void;
  /** Called when the learner clicks "Show me the answer". The parent
   * collects current editor content + readonly files and drives the API. */
  onShowAnswer?: () => void;
  /** True while the parent is in the middle of a show-answer call. */
  showAnswerPending?: boolean;
  /** Returns the learner's current editor contents (path → body). The
   * mentor ships this with every chat request so it never has to ask the
   * learner to paste their code. Empty map for read-only lessons. */
  getFilesSnapshot?: () => Record<string, string>;
};

export const MentorChat = forwardRef<MentorChatHandle, Props>(
  function MentorChat(
    {
      challengeId,
      onJumpToCode,
      onShowAnswer,
      showAnswerPending = false,
      getFilesSnapshot,
    },
    ref,
  ) {
    const [turns, setTurns] = useState<Turn[]>([]);
    const [message, setMessage] = useState("");
    const [hintLevel, setHintLevel] = useState<1 | 2 | 3>(1);
    const [pending, setPending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [historyOpen, setHistoryOpen] = useState(false);
    const rootRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
      (async () => {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session) return;
        const res = await fetch(
          `${API_BASE_URL}/api/ai/messages/${challengeId}`,
          {
            headers: { Authorization: `Bearer ${session.access_token}` },
            cache: "no-store",
          },
        );
        if (res.ok) setTurns(await res.json());
      })();
    }, [challengeId]);

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
        body: JSON.stringify({
          challenge_id: challengeId,
          message: text,
          hint_level: level,
          current_files: getFilesSnapshot ? getFilesSnapshot() : {},
        }),
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

    async function quickHint(level: 1 | 2 | 3) {
      if (pending) return;
      setHintLevel(level);
      const text = `Give me a Hint level ${level} for my current state on this challenge. Don't reveal the full code.`;
      await postChat(text, level);
    }

    function maybeScrollMentorIntoView() {
      // On lg+, the mentor is sticky-pinned and already in view — scrolling
      // would jerk the page. Only scroll on smaller viewports where the
      // mentor lives below the runner.
      if (typeof window === "undefined") return;
      if (window.matchMedia("(min-width: 1024px)").matches) return;
      rootRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    useImperativeHandle(
      ref,
      () => ({
        async askMentor(text: string, level: 1 | 2 | 3 = 2) {
          setHintLevel(level);
          maybeScrollMentorIntoView();
          await postChat(text, level);
        },
        scrollIntoView() {
          maybeScrollMentorIntoView();
        },
        appendAssistantNotice(text: string) {
          setTurns((prev) => [
            ...prev,
            {
              id: `local-${Date.now()}`,
              role: "assistant",
              content: text,
              hint_level: null,
              created_at: new Date().toISOString(),
            },
          ]);
        },
      }),
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [challengeId],
    );

    async function clear() {
      if (turns.length === 0) return;
      if (!confirm("Clear the entire mentor conversation for this challenge?"))
        return;
      setError(null);
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setError("Sign in to clear the chat.");
        return;
      }
      const response = await fetch(
        `${API_BASE_URL}/api/ai/messages/${challengeId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${session.access_token}` },
        },
      );
      if (!response.ok) {
        const body = await response.text();
        setError(`Clear failed (${response.status}): ${body.slice(0, 200)}`);
        return;
      }
      setTurns([]);
    }

    // One backwards pass: pick the most recent assistant + user turn (those
    // become the primary view) and bucket everything else as history.
    let latestAssistant: Turn | undefined;
    let latestUser: Turn | undefined;
    const historyTurns: Turn[] = [];
    for (let i = turns.length - 1; i >= 0; i--) {
      const t = turns[i];
      if (!latestAssistant && t.role === "assistant") {
        latestAssistant = t;
        continue;
      }
      if (!latestUser && t.role === "user") {
        latestUser = t;
        continue;
      }
      historyTurns.unshift(t);
    }

    return (
      <section
        ref={rootRef}
        className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-border bg-background"
      >
        <header className="border-b border-border px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold">AI mentor</h3>
            <button
              type="button"
              onClick={clear}
              disabled={turns.length === 0}
              className="rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted disabled:opacity-40"
              title="Delete all mentor messages for this challenge"
            >
              Clear
            </button>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-2">
            {[1, 2, 3].map((level) => (
              <button
                key={level}
                type="button"
                onClick={() => quickHint(level as 1 | 2 | 3)}
                disabled={pending}
                className={cn(
                  "rounded-md border px-2 py-2 text-xs font-medium",
                  hintLevel === level && pending
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-background text-foreground hover:bg-muted",
                  pending && "cursor-wait opacity-60",
                )}
                title={
                  level === 1
                    ? "Hint 1 — Socratic: asks a question, doesn't give the answer"
                    : level === 2
                      ? "Hint 2 — points at the file/function to look at"
                      : "Hint 3 — sketches pseudocode"
                }
              >
                Hint {level}
              </button>
            ))}
          </div>
          {onShowAnswer && (
            <button
              type="button"
              onClick={onShowAnswer}
              disabled={showAnswerPending || pending}
              className="mt-2 w-full rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900 hover:bg-amber-100 disabled:opacity-60"
              title="Replace your code with a working version"
            >
              {showAnswerPending ? "Generating answer…" : "Show me the answer"}
            </button>
          )}
          <p className="mt-2 text-sm text-muted-foreground">
            Click a <Glossary term="hint">Hint button</Glossary> for help at
            that level. Each new hint replaces the previous one.
          </p>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {pending && (
            <div className="rounded-md border border-border bg-muted/30 p-3 text-xs text-muted-foreground">
              Mentor is thinking…
            </div>
          )}

          {!pending && !latestAssistant && (
            <p className="text-sm text-muted-foreground">
              Click a Hint button above, or type a question below.
            </p>
          )}

          {latestUser && (
            <div className="rounded-md bg-muted/40 px-3 py-2">
              <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                You
              </p>
              <p className="whitespace-pre-wrap text-sm">
                {latestUser.content}
              </p>
            </div>
          )}

          {latestAssistant && (
            <div className="rounded-md border border-border bg-background px-3 py-2">
              <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                Mentor
                {latestAssistant.hint_level !== null &&
                  ` · hint ${latestAssistant.hint_level}`}
              </p>
              <MentorMessage
                text={latestAssistant.content}
                onJumpToCode={onJumpToCode}
              />
            </div>
          )}

          {historyTurns.length > 0 && (
            <details
              className="rounded-md border border-border bg-muted/10 text-xs"
              open={historyOpen}
              onToggle={(e) =>
                setHistoryOpen((e.target as HTMLDetailsElement).open)
              }
            >
              <summary className="cursor-pointer px-3 py-2 text-muted-foreground hover:text-foreground">
                Earlier conversation ({historyTurns.length})
              </summary>
              <div className="space-y-2 border-t border-border p-3">
                {historyTurns.map((t) => (
                  <div
                    key={t.id}
                    className={`rounded px-2 py-1.5 ${
                      t.role === "user"
                        ? "bg-muted/40"
                        : "bg-background border border-border"
                    }`}
                  >
                    <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                      {t.role}
                      {t.hint_level !== null && ` · hint ${t.hint_level}`}
                    </p>
                    {t.role === "assistant" ? (
                      <MentorMessage
                        text={t.content}
                        onJumpToCode={onJumpToCode}
                      />
                    ) : (
                      <p className="whitespace-pre-wrap text-sm">{t.content}</p>
                    )}
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>

        <form onSubmit={send} className="space-y-2 border-t border-border p-4">
          <textarea
            rows={2}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Or type your own question…"
            className="block w-full resize-none rounded-md border border-border bg-background px-3 py-2 text-sm"
          />
          {error && <p className="text-xs text-red-600">{error}</p>}
          <Button
            type="submit"
            disabled={pending || !message.trim()}
            className="w-full"
          >
            {pending ? "Thinking…" : "Ask"}
          </Button>
        </form>
      </section>
    );
  },
);
