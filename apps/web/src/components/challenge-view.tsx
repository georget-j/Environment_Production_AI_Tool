"use client";

import { useCallback, useRef, useState } from "react";
import {
  ChallengeRunner,
  type ChallengeRunnerHandle,
} from "@/components/challenge-runner";
import { CodePreview } from "@/components/code-preview";
import { MentorChat, type MentorChatHandle } from "@/components/mentor-chat";
import { OnboardingTour } from "@/components/onboarding-tour";
import { ShowAnswerModal } from "@/components/show-answer-modal";
import type { ChallengeRunnerConfig } from "@/lib/featured-files";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Props = {
  challengeId: string;
  challengeSlug: string;
  repoTemplateUrl: string | null;
  repoBranch: string | null;
  config: ChallengeRunnerConfig | undefined;
  /** Left column: scenario / goal / instructions / sidebar info. */
  left: React.ReactNode;
};

/**
 * Owns the runner + mentor wiring and lays them out as a 3-col grid on lg+
 * (left context · workspace · pinned mentor sidebar), falling back to a single
 * stacked column on smaller viewports.
 *
 *  - Holds an imperative handle to the ChallengeRunner so the mentor's inline
 *    file:line links and the show-answer flow can drive the editor.
 *  - Captures the latest file map snapshot via onFilesChange so show-answer
 *    has something to send to the API.
 */
export function ChallengeView({
  challengeId,
  challengeSlug,
  repoTemplateUrl,
  repoBranch,
  config,
  left,
}: Props) {
  const mentorRef = useRef<MentorChatHandle | null>(null);
  const runnerRef = useRef<ChallengeRunnerHandle | null>(null);
  const filesRef = useRef<Record<string, string>>({});
  const [showAnswerOpen, setShowAnswerOpen] = useState(false);
  const [showAnswerPending, setShowAnswerPending] = useState(false);

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
    try {
      // Lazy import to keep this off the initial bundle.
      const { createClient } = await import("@/lib/supabase/client");
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        alert("Please sign in first.");
        return;
      }

      const allFiles = filesRef.current;
      const editable: Record<string, string> = {};
      const readonly: Record<string, string> = {};
      for (const [path, body] of Object.entries(allFiles)) {
        if (config.editable.includes(path)) editable[path] = body;
        else readonly[path] = body;
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
        alert(`Show-answer failed (${response.status}): ${body.slice(0, 200)}`);
        return;
      }
      const data = (await response.json()) as {
        fixed_files: { path: string; content: string }[];
        summary: string;
      };
      const next: Record<string, string> = {};
      for (const f of data.fixed_files) next[f.path] = f.content;
      runnerRef.current?.applyFiles(next);

      // Mark locally so we can show 'answer-viewed' later.
      if (typeof window !== "undefined") {
        window.localStorage.setItem(`prodready:answer-viewed:${challengeSlug}`, "1");
      }

      // Push the summary into the mentor chat (client-side only).
      mentorRef.current?.appendAssistantNotice(
        `Here's a working version. ${data.summary}\n\nClick Run tests to confirm it passes.`,
      );
      mentorRef.current?.scrollIntoView();
      setShowAnswerOpen(false);
    } finally {
      setShowAnswerPending(false);
    }
  }, [challengeId, challengeSlug, config]);

  const runner =
    config?.mode === "pyodide" && repoTemplateUrl ? (
      <ChallengeRunner
        ref={runnerRef}
        challengeSlug={challengeSlug}
        challengeId={challengeId}
        repoTemplateUrl={repoTemplateUrl}
        branch={repoBranch ?? "main"}
        config={config}
        onStuck={handleStuck}
        onFilesChange={handleFilesChange}
      />
    ) : (
      <CodePreview
        repoTemplateUrl={repoTemplateUrl}
        branch={repoBranch}
        paths={config?.mode === "reading" ? config.readonly : []}
      />
    );

  const mentor = (
    <MentorChat
      ref={mentorRef}
      challengeId={challengeId}
      onJumpToCode={handleJumpToCode}
      onShowAnswer={config?.mode === "pyodide" ? () => setShowAnswerOpen(true) : undefined}
      showAnswerPending={showAnswerPending}
    />
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,_1fr)_minmax(0,_1.6fr)_380px] lg:items-start">
      <article className="space-y-6 lg:sticky lg:top-6 lg:self-start">{left}</article>

      <section className="space-y-6 min-w-0">{runner}</section>

      <aside className="lg:sticky lg:top-6 lg:self-start lg:h-[calc(100vh-3rem)]">
        {mentor}
      </aside>

      <ShowAnswerModal
        open={showAnswerOpen}
        pending={showAnswerPending}
        onCancel={() => setShowAnswerOpen(false)}
        onConfirm={handleShowAnswerConfirm}
      />

      <OnboardingTour />
    </div>
  );
}
