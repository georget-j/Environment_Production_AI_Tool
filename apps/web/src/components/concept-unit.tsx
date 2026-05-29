"use client";

/**
 * The 6-stage UNIT shell for a single concept atom (Mental Models track).
 *
 * Stages: Try → Read → Play → Check → Apply → Reflect.
 *
 * Try is non-blocking (productive-failure record). The other five gate
 * mastery. CC.1 ships Try / Read / Check / Reflect as functional stages
 * and Play / Apply as placeholders — Play widgets land in CC.2 and the
 * Apply hand-off to existing skeleton/fillblank lessons lands in CC.5.
 */

import Link from "next/link";
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  type ConceptDetail,
  type ConceptMCQ,
  type ConceptStageProgress,
  type ReflectGradeResponse,
  gradeReflect,
  markStageComplete,
  recordTryAttempt,
} from "@/lib/concepts";
import { Button } from "@/components/ui/button";
import { ConceptApplyRunner } from "@/components/concept-apply-runner";
import { ConceptMentor } from "@/components/concept-mentor";
import { ConceptPlay } from "@/components/concept-play";
import { createClient } from "@/lib/supabase/client";

type Stage = "try" | "read" | "play" | "check" | "apply" | "reflect";

const STAGE_ORDER: Stage[] = [
  "try",
  "read",
  "play",
  "check",
  "apply",
  "reflect",
];
const STAGE_LABELS: Record<Stage, string> = {
  try: "Try",
  read: "Read",
  play: "Play",
  check: "Check",
  apply: "Apply",
  reflect: "Reflect",
};

/** Is the given stage's persisted completion timestamp set? Try is
 * special-cased — it counts as "done" when the learner has saved any
 * attempt (even an empty one is fine; the system records the attempt
 * itself, not its correctness). */
function isStageComplete(
  stage: Stage,
  progress: ConceptStageProgress | null,
): boolean {
  if (!progress) return false;
  const key = stage === "try" ? "try_attempted_at" : `${stage}_completed_at`;
  // @ts-expect-error -- string indexing the progress shape
  return progress[key] != null;
}

export function ConceptUnit({ concept }: { concept: ConceptDetail }) {
  const [progress, setProgress] = useState<ConceptStageProgress | null>(
    concept.progress,
  );
  const [stage, setStage] = useState<Stage>(() =>
    firstIncompleteStage(concept.progress),
  );
  // Mobile slide-up sheet visibility for the mentor. On lg+ the panel
  // sits in the right column and this flag is ignored.
  const [mentorOpen, setMentorOpen] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <Link
          href="/tracks/mental-models"
          className="inline-flex w-fit items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground hover:text-foreground"
        >
          <span aria-hidden="true">←</span>
          <span>
            {concept.layer === "universal"
              ? "Universal CS foundation"
              : "Mental Models"}
          </span>
        </Link>
        <h1 className="text-2xl font-semibold leading-tight">
          {concept.title}
        </h1>
        <p className="text-sm text-muted-foreground">{concept.one_line}</p>
      </header>

      <ProgressBar stage={stage} progress={progress} onJumpTo={setStage} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <main className="min-h-[400px] rounded-lg border border-border bg-background p-5">
          {stage === "try" && (
            <TryStage
              concept={concept}
              progress={progress}
              onProgressChange={setProgress}
              onAdvance={() => setStage("read")}
            />
          )}
          {stage === "read" && (
            <ReadStage
              concept={concept}
              progress={progress}
              onProgressChange={setProgress}
              onAdvance={() => setStage("play")}
            />
          )}
          {stage === "play" && (
            <PlayStage
              concept={concept}
              progress={progress}
              onProgressChange={setProgress}
              onAdvance={() => setStage("check")}
            />
          )}
          {stage === "check" && (
            <CheckStage
              concept={concept}
              progress={progress}
              onProgressChange={setProgress}
              onAdvance={() => setStage("apply")}
            />
          )}
          {stage === "apply" && (
            <ApplyStage
              concept={concept}
              progress={progress}
              onProgressChange={setProgress}
              onAdvance={() => setStage("reflect")}
            />
          )}
          {stage === "reflect" && (
            <ReflectStage
              concept={concept}
              progress={progress}
              onProgressChange={setProgress}
            />
          )}
        </main>

        {/* lg+ right-rail mentor */}
        <div className="hidden lg:block">
          <ConceptMentor conceptSlug={concept.slug} stage={stage} />
        </div>
      </div>

      {/* Mobile / md: floating button + slide-up sheet */}
      <button
        type="button"
        onClick={() => setMentorOpen(true)}
        className="fixed bottom-4 right-4 z-30 rounded-full bg-foreground px-4 py-3 text-sm font-medium text-background shadow-lg lg:hidden"
        aria-label="Ask the mentor"
      >
        Ask the mentor
      </button>
      {mentorOpen && (
        <div className="fixed inset-0 z-40 flex flex-col lg:hidden">
          <button
            type="button"
            onClick={() => setMentorOpen(false)}
            className="flex-1 bg-black/40"
            aria-label="Close mentor"
          />
          <div className="max-h-[80vh] overflow-hidden rounded-t-lg border-t border-border bg-background shadow-xl">
            <div className="flex items-center justify-between border-b border-border px-3 py-2">
              <p className="text-sm font-semibold">Mentor</p>
              <button
                type="button"
                onClick={() => setMentorOpen(false)}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Close
              </button>
            </div>
            <div className="overflow-y-auto p-3">
              <ConceptMentor conceptSlug={concept.slug} stage={stage} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------- helpers ---------- //

function firstIncompleteStage(progress: ConceptStageProgress | null): Stage {
  if (!progress) return "try";
  for (const s of STAGE_ORDER) {
    if (!isStageComplete(s, progress)) return s;
  }
  return "reflect";
}

async function getAccessToken(): Promise<string | null> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

// ---------- progress bar ---------- //

function ProgressBar({
  stage,
  progress,
  onJumpTo,
}: {
  stage: Stage;
  progress: ConceptStageProgress | null;
  onJumpTo: (s: Stage) => void;
}) {
  return (
    <ol className="flex flex-wrap items-center gap-1 rounded-md border border-border bg-muted/30 p-1 text-xs">
      {STAGE_ORDER.map((s) => {
        const done = isStageComplete(s, progress);
        const active = s === stage;
        return (
          <li key={s} className="flex-1">
            <button
              type="button"
              onClick={() => onJumpTo(s)}
              className={`flex w-full items-center justify-center gap-1 rounded px-2 py-1.5 transition-colors ${
                active
                  ? "bg-background font-semibold text-foreground shadow-sm"
                  : done
                    ? "text-green-700 hover:bg-background/60"
                    : "text-muted-foreground hover:bg-background/60"
              }`}
            >
              <span aria-hidden="true">{done ? "✓" : ""}</span>
              <span>{STAGE_LABELS[s]}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

// ---------- stages ---------- //

type StageProps = {
  concept: ConceptDetail;
  progress: ConceptStageProgress | null;
  onProgressChange: (p: ConceptStageProgress) => void;
  onAdvance: () => void;
};

// Reflect is the terminal stage and never advances.
type TerminalStageProps = Omit<StageProps, "onAdvance">;

function TryStage({
  concept,
  progress,
  onProgressChange,
  onAdvance,
}: StageProps) {
  const [text, setText] = useState(progress?.try_attempt_text ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Not signed in.");
      const res = await recordTryAttempt(token, concept.slug, text);
      onProgressChange(res.progress);
      onAdvance();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-md border-2 border-amber-300 bg-amber-50 p-3 text-xs font-medium text-amber-900">
        <strong>Productive failure:</strong> attempt this <em>before</em> any
        teaching. Don&apos;t worry about being right — guessing and being wrong
        is part of how this works.
      </div>
      <article className="prose prose-sm max-w-none">
        <ReactMarkdown>{concept.try_prompt_md}</ReactMarkdown>
      </article>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Your attempt</span>
        <textarea
          rows={5}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Your best guess + a one-line reason. Anything is fine."
          className="rounded-md border border-border bg-background p-3 font-mono text-xs focus:border-foreground focus:outline-none"
        />
      </label>
      {error && <p className="text-xs text-red-700">{error}</p>}
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onAdvance}
          className="text-xs text-muted-foreground underline-offset-4 hover:underline"
        >
          Skip → Read
        </button>
        <Button onClick={submit} disabled={saving}>
          {saving ? "Saving…" : "Save attempt → Read"}
        </Button>
      </div>
    </div>
  );
}

/** Block in a parsed Read-stage exposition. The parser breaks markdown
 * into discrete visual blocks so each idea gets its own card, instead of
 * one prose blob the eye slides off. */
type ReadBlock =
  | { kind: "paragraph"; text: string }
  | { kind: "bullets"; items: string[] }
  | { kind: "code"; body: string };

/** Lightweight markdown segmenter for the Read stage. Splits on blank
 * lines, then classifies each segment. Each bullet becomes its own block
 * (rendered as a separate card). Fenced ```code``` blocks are kept whole.
 *
 * We're not building a real markdown parser — just enough segmentation
 * to drive a clean visual layout. ReactMarkdown still handles inline
 * formatting (bold, inline code, links) within each block. */
function parseExposition(md: string): ReadBlock[] {
  const blocks: ReadBlock[] = [];
  const text = md.replace(/\r\n/g, "\n").trim();
  let i = 0;
  while (i < text.length) {
    // Code fence — preserve verbatim.
    if (text.startsWith("```", i)) {
      const end = text.indexOf("```", i + 3);
      if (end === -1) {
        blocks.push({ kind: "paragraph", text: text.slice(i) });
        break;
      }
      const fence = text.slice(i, end + 3);
      const body = fence.replace(/^```\w*\n?/, "").replace(/```$/, "");
      blocks.push({ kind: "code", body });
      i = end + 3;
      while (i < text.length && text[i] === "\n") i++;
      continue;
    }
    // Take until the next blank line.
    const blank = text.indexOf("\n\n", i);
    const next = blank === -1 ? text.length : blank;
    const segment = text.slice(i, next).trim();
    if (segment) {
      if (/^[-*]\s/.test(segment)) {
        const items = segment
          .split("\n")
          .filter((l) => /^[-*]\s/.test(l.trim()))
          .map((l) => l.trim().replace(/^[-*]\s+/, ""));
        blocks.push({ kind: "bullets", items });
      } else {
        blocks.push({ kind: "paragraph", text: segment });
      }
    }
    i = next + 2;
  }
  return blocks;
}

function ReadStage({
  concept,
  progress,
  onProgressChange,
  onAdvance,
}: StageProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tryAttempt = progress?.try_attempt_text?.trim() ?? "";
  const blocks = useMemo(
    () => parseExposition(concept.exposition_md ?? ""),
    [concept.exposition_md],
  );

  async function advance() {
    setBusy(true);
    setError(null);
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Not signed in.");
      const res = await markStageComplete(token, concept.slug, "read");
      onProgressChange(res.progress);
      onAdvance();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to save.");
    } finally {
      setBusy(false);
    }
  }

  // Tight prose token reused inside cards — keeps paragraph margins flat
  // so the card padding does the spacing.
  const proseInline =
    "prose prose-base max-w-none prose-p:my-0 prose-strong:font-semibold prose-em:italic prose-code:rounded prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:font-mono prose-code:text-[0.88em] prose-code:before:content-none prose-code:after:content-none";

  return (
    <div className="flex flex-col gap-5">
      {tryAttempt && (
        <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
          <p className="font-semibold">You tried:</p>
          <p className="mt-1 whitespace-pre-wrap font-mono">{tryAttempt}</p>
        </div>
      )}

      <div className="rounded-lg border-2 border-foreground/15 bg-gradient-to-br from-muted/40 to-muted/10 p-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          The idea
        </p>
        <p className="mt-1.5 text-base font-medium leading-snug">
          {concept.one_line}
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {blocks.map((b, i) => {
          if (b.kind === "paragraph") {
            return (
              <div key={i} className={proseInline}>
                <ReactMarkdown>{b.text}</ReactMarkdown>
              </div>
            );
          }
          if (b.kind === "bullets") {
            return (
              <ul key={i} className="flex flex-col gap-2">
                {b.items.map((item, j) => (
                  <li
                    key={j}
                    className="flex gap-3 rounded-md border border-border bg-background p-3"
                  >
                    <span
                      aria-hidden="true"
                      className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-foreground/50"
                    />
                    <div className={proseInline}>
                      <ReactMarkdown>{item}</ReactMarkdown>
                    </div>
                  </li>
                ))}
              </ul>
            );
          }
          // code block in the exposition (rare — most concepts keep code in worked_example_md)
          return (
            <pre
              key={i}
              className="overflow-x-auto rounded-md border border-border bg-muted/40 p-3 font-mono text-sm"
            >
              {b.body}
            </pre>
          );
        })}
      </div>

      {concept.worked_example_md?.trim() && (
        <div className="rounded-md border border-border bg-muted/20">
          <p className="border-b border-border px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Worked example
          </p>
          <div className="prose prose-base max-w-none p-3 prose-pre:my-0 prose-pre:overflow-x-auto prose-pre:bg-foreground prose-pre:p-3 prose-pre:text-background prose-pre:text-sm prose-code:font-mono prose-code:text-[0.95em]">
            <ReactMarkdown>{concept.worked_example_md}</ReactMarkdown>
          </div>
        </div>
      )}

      {error && <p className="text-xs text-red-700">{error}</p>}
      <div className="flex justify-end">
        <Button onClick={advance} disabled={busy}>
          {busy ? "Saving…" : "Got it → Play"}
        </Button>
      </div>
    </div>
  );
}

function PlayStage({ concept, onProgressChange, onAdvance }: StageProps) {
  // The widget host dispatches on the concept's play_widget_kind. The
  // mastery roll-forward fires when the host calls onComplete.
  return (
    <ConceptPlay
      widgetKind={concept.play_widget_kind}
      widgetConfig={concept.play_widget_json}
      onComplete={async () => {
        const token = await getAccessToken();
        if (!token) return;
        const res = await markStageComplete(token, concept.slug, "play");
        onProgressChange(res.progress);
        onAdvance();
      }}
    />
  );
}

function CheckStage({ concept, onProgressChange, onAdvance }: StageProps) {
  // 2-3 MCQs. All must be correct on a single attempt. Wrong answers
  // surface the relevant Read section (CC.1 simplification: just show a
  // 'review the Read' tooltip rather than scrolling to a section).
  const mcqs = useMemo(
    () => concept.check_mcqs_json ?? [],
    [concept.check_mcqs_json],
  );
  const total = mcqs.length;
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);

  const wrong = useMemo(() => {
    if (!submitted) return [];
    return mcqs
      .map((m: ConceptMCQ, i: number) => ({ idx: i, mcq: m }))
      .filter(({ idx, mcq }) => answers[idx] !== mcq.correct);
  }, [submitted, mcqs, answers]);

  async function submit() {
    setSubmitted(true);
    const allCorrect =
      mcqs.length > 0 &&
      mcqs.every((m: ConceptMCQ, i: number) => answers[i] === m.correct);
    if (!allCorrect) return;
    setBusy(true);
    try {
      const token = await getAccessToken();
      if (!token) return;
      const res = await markStageComplete(token, concept.slug, "check");
      onProgressChange(res.progress);
      onAdvance();
    } finally {
      setBusy(false);
    }
  }

  function retake() {
    setSubmitted(false);
    setAnswers({});
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        {total} quick check{total === 1 ? "" : "s"}. Pick all the right answers
        in a single attempt — wrong ones bounce you back to the Read.
      </p>
      <ol className="flex flex-col gap-4">
        {mcqs.map((mcq: ConceptMCQ, qi: number) => {
          const chosen = answers[qi];
          const correct = mcq.correct;
          const isCorrect = submitted && chosen === correct;
          const isWrong = submitted && chosen !== correct;
          return (
            <li key={qi} className="rounded-md border border-border p-3">
              <div className="flex gap-2 text-sm font-medium">
                <span className="shrink-0">{qi + 1}.</span>
                <div className="prose prose-sm max-w-none prose-p:my-0 prose-pre:my-2 prose-pre:bg-muted prose-pre:text-foreground prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:text-[0.85em] prose-code:before:content-none prose-code:after:content-none">
                  <ReactMarkdown>{mcq.q}</ReactMarkdown>
                </div>
              </div>
              <ul className="mt-3 flex flex-col gap-1">
                {mcq.options.map((opt: string, oi: number) => {
                  const picked = chosen === oi;
                  const showCorrect = submitted && oi === correct;
                  return (
                    <li key={oi}>
                      <label
                        className={`flex cursor-pointer items-start gap-2 rounded px-2 py-1.5 text-sm ${
                          showCorrect
                            ? "bg-green-50 text-green-900"
                            : picked && submitted
                              ? "bg-red-50 text-red-900"
                              : picked
                                ? "bg-muted"
                                : "hover:bg-muted/60"
                        }`}
                      >
                        <input
                          type="radio"
                          name={`mcq-${qi}`}
                          checked={picked}
                          onChange={() =>
                            setAnswers((a) => ({ ...a, [qi]: oi }))
                          }
                          disabled={submitted}
                          className="mt-1 shrink-0"
                        />
                        <div className="prose prose-sm max-w-none prose-p:my-0 prose-code:rounded prose-code:bg-background/60 prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:text-[0.85em] prose-code:before:content-none prose-code:after:content-none">
                          <ReactMarkdown>{opt}</ReactMarkdown>
                        </div>
                      </label>
                    </li>
                  );
                })}
              </ul>
              {isCorrect && mcq.why && (
                <div className="prose prose-xs mt-2 max-w-none text-xs text-green-800 prose-p:my-0 prose-code:rounded prose-code:bg-green-100 prose-code:px-1 prose-code:font-mono prose-code:text-[0.9em] prose-code:before:content-none prose-code:after:content-none">
                  <strong>Correct — </strong>
                  <ReactMarkdown>{mcq.why}</ReactMarkdown>
                </div>
              )}
              {isWrong && mcq.why && (
                <div className="prose prose-xs mt-2 max-w-none text-xs text-red-800 prose-p:my-0 prose-code:rounded prose-code:bg-red-100 prose-code:px-1 prose-code:font-mono prose-code:text-[0.9em] prose-code:before:content-none prose-code:after:content-none">
                  <strong>Not quite. </strong>
                  <ReactMarkdown>{mcq.why}</ReactMarkdown>
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {!submitted && (
        <div className="flex justify-end">
          <Button
            onClick={submit}
            disabled={Object.keys(answers).length < total}
          >
            Check answers
          </Button>
        </div>
      )}
      {submitted && wrong.length === 0 && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-green-300 bg-green-50 p-3 text-sm text-green-900">
          <span>✓ All correct.</span>
          <Button onClick={() => onAdvance()} disabled={busy}>
            {busy ? "…" : "Next → Apply"}
          </Button>
        </div>
      )}
      {submitted && wrong.length > 0 && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <span>
            {wrong.length} answer{wrong.length === 1 ? "" : "s"} need
            revisiting. Go back to the Read for the relevant section, then try
            again.
          </span>
          <button
            type="button"
            onClick={retake}
            className="text-sm underline underline-offset-4"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * ApplyStage — real Pyodide runner (M2). Dispatches on which Apply mode
 * the concept declares:
 *   - apply_skeleton_json  → inline Pyodide runner (instructions + textarea + pytest)
 *   - apply_challenge_slug → link to an existing challenge
 *   - neither              → legacy placeholder + "Mark complete" escape hatch
 */
function ApplyStage({ concept, onProgressChange, onAdvance }: StageProps) {
  const [busy, setBusy] = useState(false);

  async function markComplete() {
    const token = await getAccessToken();
    if (!token) return;
    const res = await markStageComplete(token, concept.slug, "apply");
    onProgressChange(res.progress);
    onAdvance();
  }

  if (concept.apply_skeleton_json) {
    return (
      <ConceptApplyRunner
        skeleton={concept.apply_skeleton_json}
        onPass={markComplete}
      />
    );
  }

  if (concept.apply_challenge_slug) {
    return (
      <div className="flex flex-col gap-4 text-sm">
        <p className="font-semibold">Apply this concept on a real task.</p>
        <p>
          This concept&apos;s Apply lesson is the existing challenge{" "}
          <code className="rounded bg-muted px-1">
            {concept.apply_challenge_slug}
          </code>
          . Complete it there, then return here to Reflect.
        </p>
        <div className="flex justify-end">
          <Link href={`/challenges/${concept.apply_challenge_slug}`}>
            <Button>Open the Apply challenge →</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Last-resort fallback so the flow never hard-blocks if a future concept
  // is authored without either Apply mode.
  async function advance() {
    setBusy(true);
    try {
      await markComplete();
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="flex flex-col gap-4 text-sm">
      <p className="font-semibold">Apply stage.</p>
      <p className="text-muted-foreground">
        No runnable Apply is attached to this concept yet. You can mark this
        stage complete and continue.
      </p>
      <div className="flex justify-end">
        <Button onClick={advance} disabled={busy}>
          {busy ? "…" : "Mark Apply complete → Reflect"}
        </Button>
      </div>
    </div>
  );
}

function ReflectStage({
  concept,
  progress,
  onProgressChange,
}: TerminalStageProps) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [verdict, setVerdict] = useState<ReflectGradeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isMastered = progress?.mastered_at != null;

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Not signed in.");
      const res = await gradeReflect(token, concept.slug, text);
      setVerdict(res);
      onProgressChange(res.progress);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to grade.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm">{concept.reflect_question}</p>
      <textarea
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Two sentences. No code needed."
        className="rounded-md border border-border bg-background p-3 text-sm focus:border-foreground focus:outline-none"
        disabled={isMastered}
      />
      {error && <p className="text-xs text-red-700">{error}</p>}
      {verdict && verdict.verdict === "shallow" && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <p className="font-semibold">A bit too short.</p>
          {verdict.follow_up && <p className="mt-1">{verdict.follow_up}</p>}
        </div>
      )}
      {verdict && verdict.verdict === "complete" && (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-green-300 bg-green-50 p-3 text-sm text-green-900">
            <div>
              <p className="font-semibold">✓ Concept mastered.</p>
              <p className="mt-1">
                You&apos;ll see this concept again in your spaced-recall queue
                in about a day.
              </p>
            </div>
            <Link
              href="/tracks/mental-models"
              className="shrink-0 rounded-md border border-green-700 bg-white px-3 py-1.5 text-sm font-medium text-green-900 hover:bg-green-100"
            >
              Pick the next concept →
            </Link>
          </div>
          {verdict.follow_up && (
            <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
              <p className="font-semibold">One thing to think about:</p>
              <p className="mt-1">{verdict.follow_up}</p>
            </div>
          )}
        </div>
      )}
      {!isMastered && (
        <div className="flex justify-end">
          <Button onClick={submit} disabled={busy || text.trim().length < 10}>
            {busy
              ? "Grading…"
              : verdict?.verdict === "shallow"
                ? "Try again"
                : "Submit"}
          </Button>
        </div>
      )}
    </div>
  );
}
