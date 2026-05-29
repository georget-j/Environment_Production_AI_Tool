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

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {concept.layer === "universal"
            ? "Universal CS foundation"
            : "Mental Models"}
        </p>
        <h1 className="text-2xl font-semibold leading-tight">
          {concept.title}
        </h1>
        <p className="text-sm text-muted-foreground">{concept.one_line}</p>
      </header>

      <ProgressBar stage={stage} progress={progress} onJumpTo={setStage} />

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
          <ApplyStagePlaceholder
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

function ReadStage({
  concept,
  progress,
  onProgressChange,
  onAdvance,
}: StageProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Surface the learner's Try attempt inline if they recorded one — that
  // turns the Read into a personalised "you tried X, here's why" moment
  // (the productive-failure dividend).
  const tryAttempt = progress?.try_attempt_text?.trim() ?? "";

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

  return (
    <div className="flex flex-col gap-5">
      {tryAttempt && (
        <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
          <p className="font-semibold">You tried:</p>
          <p className="mt-1 whitespace-pre-wrap font-mono">{tryAttempt}</p>
        </div>
      )}
      <div className="rounded-md border border-border bg-muted/30 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          The idea, in one line
        </p>
        <p className="mt-1 text-sm font-medium">{concept.one_line}</p>
      </div>
      <article className="prose prose-sm max-w-none prose-headings:mt-4 prose-headings:mb-1 prose-p:my-2 prose-ul:my-2 prose-li:my-0.5 prose-pre:my-2">
        <ReactMarkdown>{concept.exposition_md}</ReactMarkdown>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Worked example
        </p>
        <ReactMarkdown>{concept.worked_example_md}</ReactMarkdown>
      </article>
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

function ApplyStagePlaceholder({
  concept,
  onProgressChange,
  onAdvance,
}: StageProps) {
  const [busy, setBusy] = useState(false);
  async function advance() {
    setBusy(true);
    try {
      const token = await getAccessToken();
      if (!token) return;
      const res = await markStageComplete(token, concept.slug, "apply");
      onProgressChange(res.progress);
      onAdvance();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 text-sm">
      <p className="font-semibold">Apply stage.</p>
      {concept.apply_challenge_slug ? (
        <p>
          When this stage is fully wired, it deep-links to the existing
          challenge{" "}
          <code className="rounded bg-muted px-1">
            {concept.apply_challenge_slug}
          </code>
          .
        </p>
      ) : (
        <p className="text-muted-foreground">
          No Apply challenge linked yet for this concept. CC.5 wires one per
          concept (existing skeleton/fillblank lesson reused).
        </p>
      )}
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
          <p className="font-semibold">Almost.</p>
          {verdict.follow_up && <p className="mt-1">{verdict.follow_up}</p>}
        </div>
      )}
      {verdict && verdict.verdict === "complete" && (
        <div className="rounded-md border border-green-300 bg-green-50 p-3 text-sm text-green-900">
          <p className="font-semibold">✓ Concept mastered.</p>
          <p className="mt-1">
            You&apos;ll see this concept again in your spaced-recall queue in
            about a day.
          </p>
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
