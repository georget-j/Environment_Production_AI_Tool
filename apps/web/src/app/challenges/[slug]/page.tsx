import { notFound } from "next/navigation";
import { apiFetch, type ChallengeDetail } from "@/lib/api";
import { CHALLENGE_CONFIG } from "@/lib/featured-files";
import { ChallengeView } from "@/components/challenge-view";
import { LessonContextStrip } from "@/components/lesson-context-strip";

type Params = Promise<{ slug: string }>;

export default async function ChallengeDetailPage({
  params,
}: {
  params: Params;
}) {
  const { slug } = await params;
  let challenge: ChallengeDetail;
  try {
    challenge = await apiFetch<ChallengeDetail>(`/api/challenges/${slug}`);
  } catch {
    notFound();
  }

  const config = CHALLENGE_CONFIG[challenge.slug];

  return (
    // 4rem = SiteNav (h-16). Use dvh so iOS Safari's dynamic chrome doesn't
    // hide the bottom of the workspace.
    <div className="flex h-[calc(100dvh-4rem)] flex-col gap-3 py-2">
      <LessonContextStrip
        moduleTitle={challenge.module.title}
        challengeTitle={challenge.title}
        scenario={challenge.scenario}
        learnerGoal={challenge.learner_goal}
        instructions={challenge.instructions}
        previous={challenge.previous}
        next={challenge.next}
        position={challenge.position_in_track}
        total={challenge.total_in_track}
      />

      <div className="min-h-0 flex-1">
        <ChallengeView
          challengeId={challenge.id}
          challengeSlug={challenge.slug}
          repoTemplateUrl={challenge.repo_template_url}
          repoBranch={challenge.repo_branch}
          config={config}
          nextSlug={challenge.next?.slug ?? null}
        />
      </div>
    </div>
  );
}
