"use client";

import { useCallback, useRef } from "react";
import { ChallengeRunner } from "@/components/challenge-runner";
import { CodePreview } from "@/components/code-preview";
import { MentorChat, type MentorChatHandle } from "@/components/mentor-chat";
import { OnboardingTour } from "@/components/onboarding-tour";
import type { ChallengeRunnerConfig } from "@/lib/featured-files";

type Props = {
  challengeId: string;
  challengeSlug: string;
  repoTemplateUrl: string | null;
  repoBranch: string | null;
  config: ChallengeRunnerConfig | undefined;
};

/**
 * Client-only shell that owns the MentorChat ref so the ChallengeRunner can
 * fire an `askMentor` call when the learner clicks "I'm stuck — help".
 */
export function ChallengeView({
  challengeId,
  challengeSlug,
  repoTemplateUrl,
  repoBranch,
  config,
}: Props) {
  const mentorRef = useRef<MentorChatHandle | null>(null);

  const handleStuck = useCallback((message: string) => {
    void mentorRef.current?.askMentor(message, 2);
  }, []);

  return (
    <>
      {config?.mode === "pyodide" && repoTemplateUrl ? (
        <ChallengeRunner
          challengeSlug={challengeSlug}
          challengeId={challengeId}
          repoTemplateUrl={repoTemplateUrl}
          branch={repoBranch ?? "main"}
          config={config}
          onStuck={handleStuck}
        />
      ) : (
        <CodePreview
          repoTemplateUrl={repoTemplateUrl}
          branch={repoBranch}
          paths={config?.mode === "reading" ? config.readonly : []}
        />
      )}

      <MentorChat ref={mentorRef} challengeId={challengeId} />

      <OnboardingTour />
    </>
  );
}
