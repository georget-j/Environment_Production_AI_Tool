import { notFound } from "next/navigation";
import { apiFetch, type ChallengeDetail } from "@/lib/api";
import { Markdown } from "@/components/markdown";
import { CHALLENGE_CONFIG } from "@/lib/featured-files";
import { ChallengeView } from "@/components/challenge-view";
import { LessonNav } from "@/components/lesson-nav";

type Params = Promise<{ slug: string }>;

export default async function ChallengeDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  let challenge: ChallengeDetail;
  try {
    challenge = await apiFetch<ChallengeDetail>(`/api/challenges/${slug}`);
  } catch {
    notFound();
  }

  const config = CHALLENGE_CONFIG[challenge.slug];

  return (
    <div className="space-y-8 py-6">
      <LessonNav
        previous={challenge.previous}
        next={challenge.next}
        position={challenge.position_in_track}
        total={challenge.total_in_track}
      />

      {/* Hero: full-width title + scenario + goal */}
      <header className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {challenge.module.title}
        </p>
        <h1 className="text-3xl font-semibold leading-tight lg:text-4xl">{challenge.title}</h1>
        <p className="max-w-3xl text-base leading-relaxed text-foreground">{challenge.scenario}</p>

        <div className="max-w-3xl rounded-md border-l-4 border-primary bg-muted/40 px-4 py-3 text-sm leading-relaxed">
          <span className="font-semibold">Your goal: </span>
          {challenge.learner_goal}
        </div>

        {challenge.instructions?.trim() && (
          <details className="max-w-3xl rounded-md border border-border bg-muted/10">
            <summary className="cursor-pointer px-4 py-2 text-sm font-medium hover:bg-muted/30">
              Instructions
            </summary>
            <div className="border-t border-border px-4 py-3">
              <Markdown>{challenge.instructions}</Markdown>
            </div>
          </details>
        )}
      </header>

      <ChallengeView
        challengeId={challenge.id}
        challengeSlug={challenge.slug}
        repoTemplateUrl={challenge.repo_template_url}
        repoBranch={challenge.repo_branch}
        config={config}
      />

      {/* Footer: skills + quick reference */}
      <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-border pt-6 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Skills
          </span>
          <div className="flex flex-wrap gap-1.5">
            {challenge.skills.map((s) => (
              <span
                key={s}
                className="rounded-full bg-muted px-2 py-0.5 text-xs text-foreground"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
        <details className="text-muted-foreground">
          <summary className="cursor-pointer text-xs hover:text-foreground">How this works</summary>
          <div className="mt-2 max-w-md rounded-md border border-border bg-muted/10 p-3 text-xs leading-relaxed">
            Edit the unlocked files in the workspace. Click <strong>Run tests</strong> — Python
            runs entirely inside your browser. The mentor on the right gives hints; click{" "}
            <strong>Show me the answer</strong> if you&apos;re truly stuck. Submit when all tests
            pass.
          </div>
        </details>
      </footer>
    </div>
  );
}
