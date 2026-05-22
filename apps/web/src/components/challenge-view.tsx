"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChallengeRunner,
  type ChallengeRunnerHandle,
} from "@/components/challenge-runner";
import { CodePreview } from "@/components/code-preview";
import {
  LessonApproach,
  type ApproachMode,
} from "@/components/lesson-approach";
import { LessonStages } from "@/components/lesson-stages";
import { LessonWalkthrough } from "@/components/lesson-walkthrough";
import { Markdown } from "@/components/markdown";
import { WALKTHROUGHS } from "@/lib/walkthroughs";
import { LessonCFillBlank } from "@/components/lesson-c-fill-blank";
import { LessonCWasm } from "@/components/lesson-c-wasm";
import { LessonFillBlank } from "@/components/lesson-fill-blank";
import { LessonMatplot } from "@/components/lesson-matplot";
import { LessonPredict } from "@/components/lesson-predict";
import { MentorChat, type MentorChatHandle } from "@/components/mentor-chat";
import { OnboardingTour } from "@/components/onboarding-tour";
import { ShowAnswerModal } from "@/components/show-answer-modal";
import { createClient } from "@/lib/supabase/client";
import type { ChallengeRunnerConfig } from "@/lib/featured-files";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ShowAnswerError = {
  kind: "auth" | "loading" | "no-editable" | "api";
  message: string;
};

type Props = {
  challengeId: string;
  challengeSlug: string;
  repoTemplateUrl: string | null;
  repoBranch: string | null;
  config: ChallengeRunnerConfig | undefined;
  /** Slug of the next lesson in the same track, for auto-advance on success. */
  nextSlug: string | null;
  /** One-line learner-facing goal, rendered in the approach card. */
  learnerGoal: string;
  /** Full instructions markdown (Concept + Example + verb + Expected) —
   *  surfaced inside the Approach stage as reference. */
  instructions: string;
};

/**
 * 2-column workspace shell. The page renders a full-width hero above this
 * component; ChallengeView owns:
 *   - left column: the runner (or read-only preview)
 *   - right column: the mentor sidebar (sticky on lg+)
 * Both share an imperative bridge so the mentor's file:line links and the
 * show-answer flow can drive the editor.
 */
export function ChallengeView({
  challengeId,
  challengeSlug,
  repoTemplateUrl,
  repoBranch,
  config,
  nextSlug,
  learnerGoal,
  instructions,
}: Props) {
  const mentorRef = useRef<MentorChatHandle | null>(null);
  const runnerRef = useRef<ChallengeRunnerHandle | null>(null);
  const filesRef = useRef<Record<string, string>>({});
  const [showAnswerOpen, setShowAnswerOpen] = useState(false);
  const [showAnswerPending, setShowAnswerPending] = useState(false);
  const [showAnswerError, setShowAnswerError] =
    useState<ShowAnswerError | null>(null);
  const [mentorOverlayOpen, setMentorOverlayOpen] = useState(false);
  // Mentor sidebar starts collapsed by default on lg+ so code-heavy
  // lessons get the wider editor. Choice is persisted to localStorage —
  // initial render uses the default so SSR/CSR match; the effect below
  // syncs to the stored value once the client is mounted.
  const [mentorCollapsed, setMentorCollapsed] = useState(true);
  // First-visit tooltip on the collapsed mentor rail — shown once per
  // browser, dismissed automatically the first time the learner expands
  // the mentor (or clicks the tooltip's close button).
  const [showRailTip, setShowRailTip] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("prodready:mentor-collapsed");
    if (stored === "false") setMentorCollapsed(false);
    const seen = window.localStorage.getItem("prodready:mentor-rail-tip-seen");
    if (stored !== "false" && seen !== "true") setShowRailTip(true);
  }, []);
  const dismissRailTip = useCallback(() => {
    setShowRailTip(false);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("prodready:mentor-rail-tip-seen", "true");
    }
  }, []);
  const handleToggleMentor = useCallback(() => {
    setMentorCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(
          "prodready:mentor-collapsed",
          next ? "true" : "false",
        );
      }
      return next;
    });
    dismissRailTip();
  }, [dismissRailTip]);

  // Lock body scroll + Escape-to-close while the mobile mentor overlay
  // is open. No-ops on lg+ because the overlay is hidden by CSS there.
  useEffect(() => {
    if (!mentorOverlayOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMentorOverlayOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [mentorOverlayOpen]);

  // Snapshot of the learner's current editor contents. For pyodide mode
  // it's the filesRef (kept fresh by ChallengeRunner's onFilesChange). For
  // fillblank mode the runner stores the single editable as
  // `solution.py` via its onCodeChange callback. The MentorChat ships this
  // map with every chat request so the mentor never has to ask for code.
  const getFilesSnapshot = useCallback(() => ({ ...filesRef.current }), []);

  const handleStuck = useCallback((message: string) => {
    void mentorRef.current?.askMentor(message, 2);
  }, []);

  const handleJumpToCode = useCallback((file: string, line: number | null) => {
    runnerRef.current?.jumpTo(file, line);
  }, []);

  const handleFilesChange = useCallback((files: Record<string, string>) => {
    filesRef.current = files;
  }, []);

  const handleShowAnswerConfirm = useCallback(async () => {
    if (config?.mode !== "pyodide") return;
    setShowAnswerPending(true);
    setShowAnswerError(null);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setShowAnswerError({
          kind: "auth",
          message: "Sign in to use Show me the answer.",
        });
        return;
      }
      const allFiles = filesRef.current;
      if (Object.keys(allFiles).length === 0) {
        setShowAnswerError({
          kind: "loading",
          message: "Files are still loading — try again in a moment.",
        });
        return;
      }
      const editable: Record<string, string> = {};
      const readonly: Record<string, string> = {};
      for (const [path, body] of Object.entries(allFiles)) {
        if (config.editable.includes(path)) editable[path] = body;
        else readonly[path] = body;
      }
      if (Object.keys(editable).length === 0) {
        setShowAnswerError({
          kind: "no-editable",
          message: "This challenge has no editable files.",
        });
        return;
      }
      const response = await fetch(`${API_BASE_URL}/api/ai/show-answer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          challenge_id: challengeId,
          editable_files: editable,
          readonly_files: readonly,
          test_output: null,
        }),
      });
      if (!response.ok) {
        const body = await response.text();
        setShowAnswerError({
          kind: "api",
          message: `Show-answer failed (${response.status}): ${body.slice(0, 200)}`,
        });
        return;
      }
      const data = (await response.json()) as {
        fixed_files: { path: string; content: string }[];
        summary: string;
      };
      const next: Record<string, string> = {};
      for (const f of data.fixed_files) next[f.path] = f.content;
      runnerRef.current?.applyFiles(next);

      mentorRef.current?.appendAssistantNotice(
        `Here's a working version. ${data.summary}\n\nClick Run tests to confirm it passes.`,
      );
      mentorRef.current?.scrollIntoView();
      setShowAnswerOpen(false);
    } finally {
      setShowAnswerPending(false);
    }
  }, [challengeId, config]);

  // Derive the approach-card mode from the runner config. For pyodide we
  // inspect the inline file map to distinguish debug / skeleton /
  // apifetch — the three shapes have very different attack strategies.
  // Fall back to "pyodide-other" for fetched-from-GitHub challenges (no
  // inline map) where we can't introspect content. `reading` lessons
  // get no approach card — they're display-only.
  const approachMode: ApproachMode | null = (() => {
    if (!config || config.mode === "reading") return null;
    if (config.mode === "pyodide") {
      const inline = config.inline ?? {};
      if ("mock_api.py" in inline) return "pyodide-apifetch";
      if (
        typeof inline["solution.py"] === "string" &&
        inline["solution.py"].includes("NotImplementedError")
      ) {
        return "pyodide-skeleton";
      }
      if (Object.keys(inline).length > 0) return "pyodide-debug";
      return "pyodide-other";
    }
    return config.mode;
  })();

  let runner: React.ReactNode;
  // No config for this slug = lesson was renamed/removed since the last
  // build. Surface a clear error rather than the misleading "no template"
  // path below.
  if (config === undefined) {
    runner = (
      <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-semibold">Lesson configuration missing.</p>
        <p className="mt-1">
          The slug <code>{challengeSlug}</code> doesn&apos;t have a runner
          config in this build. The lesson may have been renamed — go back to
          the{" "}
          <Link href="/tracks/quant-programmer" className="underline">
            track page
          </Link>{" "}
          and click the lesson from there.
        </p>
      </div>
    );
  } else
    switch (config?.mode) {
      case "pyodide":
        // Pyodide projects can ship inline file scaffolds (Quant mini-
        // projects) OR fetch them from a GitHub mirror (FastAPI commerce
        // challenges). Either source is fine; only error if neither is
        // available.
        runner =
          config.inline || repoTemplateUrl ? (
            <ChallengeRunner
              ref={runnerRef}
              challengeSlug={challengeSlug}
              challengeId={challengeId}
              repoTemplateUrl={repoTemplateUrl}
              branch={repoBranch ?? "main"}
              config={config}
              nextSlug={nextSlug}
              onStuck={handleStuck}
              onFilesChange={handleFilesChange}
            />
          ) : (
            <p className="rounded-md border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
              This challenge is missing a template URL — please contact support.
            </p>
          );
        break;
      case "predict":
        runner = <LessonPredict config={config} nextSlug={nextSlug} />;
        break;
      case "fillblank":
        runner = (
          <LessonFillBlank
            config={config}
            nextSlug={nextSlug}
            onCodeChange={(code) => {
              // Mirror the single editable into filesRef so MentorChat picks
              // it up via getFilesSnapshot.
              filesRef.current = { "solution.py": code };
            }}
          />
        );
        break;
      case "matplot":
        runner = (
          <LessonMatplot
            config={config}
            nextSlug={nextSlug}
            onCodeChange={(code) => {
              filesRef.current = { "solution.py": code };
            }}
          />
        );
        break;
      case "cscript":
        runner = (
          <LessonCFillBlank
            config={config}
            nextSlug={nextSlug}
            onCodeChange={(code) => {
              filesRef.current = { "solution.c": code };
            }}
          />
        );
        break;
      case "cwasm":
        runner = <LessonCWasm config={config} nextSlug={nextSlug} />;
        break;
      case "reading":
      default:
        runner = (
          <CodePreview
            repoTemplateUrl={repoTemplateUrl}
            branch={repoBranch}
            paths={config?.mode === "reading" ? config.readonly : []}
          />
        );
    }

  const mentorOnShowAnswer =
    config?.mode === "pyodide" ? () => setShowAnswerOpen(true) : undefined;

  const mentorLanguage: "python" | "c" | undefined =
    config?.mode === "cscript" ? "c" : "python";

  // On lg+, the grid's right column is either the full mentor sidebar
  // (~400px) or a thin 40px rail that the learner clicks to expand.
  // The mobile overlay flow doesn't depend on this column.
  // No h-full / min-h-0 here — we want the workspace to grow with its
  // content and the document to scroll, instead of clipping the bottom
  // action area on long lessons. The mentor column is `lg:sticky` so it
  // stays in view while the workspace scrolls.
  const gridClass = mentorCollapsed
    ? "grid h-full min-h-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,_1fr)_40px]"
    : "grid h-full min-h-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,_1fr)_minmax(360px,_400px)]";

  const walkthrough = WALKTHROUGHS[challengeSlug];
  const examplePane = walkthrough ? (
    <div className="h-full min-h-0 p-3">
      <LessonWalkthrough
        code={walkthrough.code}
        steps={walkthrough.steps}
        scrollTargetId=""
      />
    </div>
  ) : undefined;

  const approachPane = approachMode ? (
    <div className="h-full space-y-3 overflow-y-auto p-3">
      <LessonApproach
        mode={approachMode}
        challengeSlug={challengeSlug}
        learnerGoal={learnerGoal}
      />
      {instructions?.trim() && (
        <details className="rounded-md border border-border bg-muted/10 px-3 py-2 text-sm">
          <summary className="cursor-pointer text-xs font-medium text-muted-foreground hover:text-foreground">
            Show concept reference (instructions, expected output)
          </summary>
          <div className="mt-2">
            <Markdown>{instructions}</Markdown>
          </div>
        </details>
      )}
    </div>
  ) : (
    <div className="h-full p-3 text-sm text-muted-foreground">
      No approach card for this lesson mode.
    </div>
  );

  // The Solve pane scrolls internally — see
  // memory/feedback_lesson_solve_stage_must_not_clip.md for the
  // recurring bug this prevents. When tests fail and the result banner
  // grows (or a post-submit success card with auto-advance appears),
  // the bottom content must always be reachable via scroll instead of
  // being clipped by a rigid flex layout.
  const solvePane = <div className="h-full overflow-y-auto">{runner}</div>;

  return (
    <div className={gridClass}>
      <section className="min-h-0 min-w-0 overflow-hidden rounded-lg border border-border bg-background">
        <LessonStages
          example={examplePane}
          approach={approachPane}
          solve={solvePane}
        />
      </section>

      {/* Mentor: lives in the grid's right column on lg+. On smaller
       * screens the grid is single-column (workspace only) and the
       * mentor is rendered as a full-screen overlay when the floating
       * "Ask the mentor" button is tapped. Same MentorChat instance —
       * only the wrapper's position class changes. The desktop sidebar
       * also has a collapsed "rail" mode where only a vertical toggle
       * button is visible, reclaiming ~360px for the editor. */}
      <aside
        className={
          mentorOverlayOpen
            ? "fixed inset-0 z-50 flex min-h-0 min-w-0 flex-col bg-background lg:relative lg:inset-auto lg:z-auto lg:bg-transparent lg:sticky lg:top-2 lg:self-start lg:max-h-[calc(100dvh-5rem)]"
            : "hidden min-w-0 lg:flex lg:flex-col lg:sticky lg:top-2 lg:self-start lg:max-h-[calc(100dvh-5rem)]"
        }
      >
        {mentorOverlayOpen && (
          <div className="flex items-center justify-between border-b border-border bg-background px-4 py-2 lg:hidden">
            <p className="text-sm font-semibold">AI mentor</p>
            <button
              type="button"
              onClick={() => setMentorOverlayOpen(false)}
              className="rounded-md px-2 py-1 text-sm hover:bg-muted"
              aria-label="Close mentor"
            >
              ✕ Close
            </button>
          </div>
        )}
        {/* Desktop rail — only visible on lg+ when the mentor is
         * collapsed. Clicking it expands the sidebar. The overlay
         * (mobile) path always shows the full chat, never the rail. */}
        {mentorCollapsed && !mentorOverlayOpen && (
          <div className="relative hidden h-full w-full lg:block">
            <button
              type="button"
              onClick={handleToggleMentor}
              className="flex h-full w-full flex-col items-center justify-start gap-3 rounded-md border border-border bg-muted/30 py-3 text-xs font-medium text-muted-foreground hover:bg-muted/60"
              aria-label="Expand the AI mentor"
              title="Expand the AI mentor"
            >
              <span aria-hidden="true">›</span>
              <span
                className="select-none"
                style={{
                  writingMode: "vertical-rl",
                  transform: "rotate(180deg)",
                }}
              >
                Ask the mentor
              </span>
            </button>
            {showRailTip && (
              <div
                role="tooltip"
                className="absolute right-12 top-3 z-20 w-56 rounded-md border border-primary/40 bg-background p-3 text-xs shadow-lg"
              >
                <p className="font-semibold">Stuck? Ask the mentor.</p>
                <p className="mt-1 text-muted-foreground">
                  Click the rail to expand the AI mentor and get a hint, or ask
                  any question about the lesson.
                </p>
                <button
                  type="button"
                  onClick={dismissRailTip}
                  className="mt-2 text-[11px] text-muted-foreground underline-offset-2 hover:underline"
                >
                  Got it
                </button>
                <span
                  aria-hidden="true"
                  className="absolute right-[-6px] top-4 h-3 w-3 rotate-45 border-r border-t border-primary/40 bg-background"
                />
              </div>
            )}
          </div>
        )}
        <div
          className={
            mentorCollapsed && !mentorOverlayOpen
              ? "hidden"
              : "flex min-h-0 flex-1 flex-col"
          }
        >
          {/* Desktop collapse button — only on lg+, only when expanded.
           * Sits inline so it doesn't reflow the mentor's internal layout. */}
          {!mentorOverlayOpen && (
            <div className="hidden lg:flex flex-none items-center justify-end border-b border-border bg-background/60 px-2 py-1">
              <button
                type="button"
                onClick={handleToggleMentor}
                className="rounded-md px-2 py-0.5 text-[11px] text-muted-foreground hover:bg-muted"
                aria-label="Collapse the AI mentor"
                title="Collapse"
              >
                Collapse ›
              </button>
            </div>
          )}
          <div className="min-h-0 flex-1">
            <MentorChat
              ref={mentorRef}
              challengeId={challengeId}
              onJumpToCode={handleJumpToCode}
              onShowAnswer={mentorOnShowAnswer}
              showAnswerPending={showAnswerPending}
              getFilesSnapshot={getFilesSnapshot}
              language={mentorLanguage}
            />
          </div>
        </div>
      </aside>

      {/* Mobile-only floating button: opens the mentor as a full-screen
       * overlay. Hidden on lg+ where the mentor is already in view. */}
      {!mentorOverlayOpen && (
        <button
          type="button"
          onClick={() => setMentorOverlayOpen(true)}
          className="fixed bottom-4 right-4 z-40 rounded-full bg-primary px-4 py-3 text-sm font-medium text-primary-foreground shadow-lg hover:bg-primary/90 lg:hidden"
        >
          Ask the mentor
        </button>
      )}

      <ShowAnswerModal
        open={showAnswerOpen}
        pending={showAnswerPending}
        errorMessage={showAnswerError?.message ?? null}
        onCancel={() => {
          setShowAnswerOpen(false);
          setShowAnswerError(null);
        }}
        onConfirm={handleShowAnswerConfirm}
      />

      <OnboardingTour />
    </div>
  );
}
