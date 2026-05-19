import { notFound } from "next/navigation";
import { apiFetch, type ChallengeDetail } from "@/lib/api";
import { StartChallengeButton } from "@/components/start-challenge-button";
import { SubmissionForm } from "@/components/submission-form";

type Params = Promise<{ slug: string }>;

export default async function ChallengeDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  let challenge: ChallengeDetail;
  try {
    challenge = await apiFetch<ChallengeDetail>(`/api/challenges/${slug}`);
  } catch {
    notFound();
  }

  return (
    <div className="grid gap-8 py-8 md:grid-cols-[2fr_1fr]">
      <article className="space-y-8">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            {challenge.module.title}
          </p>
          <h1 className="text-3xl font-semibold">{challenge.title}</h1>
          <p className="text-muted-foreground">{challenge.scenario}</p>
        </header>

        <section>
          <h2 className="mb-2 text-lg font-semibold">Goal</h2>
          <p className="text-sm">{challenge.learner_goal}</p>
        </section>

        <section className="prose prose-sm max-w-none">
          <h2 className="mb-2 text-lg font-semibold">Instructions</h2>
          <pre className="whitespace-pre-wrap rounded-md border border-border bg-muted/30 p-4 text-sm">
            {challenge.instructions}
          </pre>
        </section>
      </article>

      <aside className="space-y-6">
        <div className="space-y-2 rounded-lg border border-border p-4">
          <h3 className="text-sm font-semibold">Repo</h3>
          {challenge.repo_template_url ? (
            <>
              <a
                href={challenge.repo_template_url}
                target="_blank"
                rel="noreferrer"
                className="block break-all text-sm text-blue-600 hover:underline"
              >
                {challenge.repo_template_url}
              </a>
              {challenge.repo_branch && (
                <p className="text-xs text-muted-foreground">Branch: {challenge.repo_branch}</p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">TBD</p>
          )}
        </div>

        <div className="space-y-2 rounded-lg border border-border p-4">
          <h3 className="text-sm font-semibold">Validation</h3>
          <pre className="overflow-x-auto rounded-md bg-muted/30 p-3 text-xs">
            {JSON.stringify(challenge.validation_config_json, null, 2)}
          </pre>
        </div>

        <div className="space-y-2 rounded-lg border border-border p-4">
          <h3 className="text-sm font-semibold">Skills</h3>
          <p className="text-xs text-muted-foreground">{challenge.skills.join(" · ")}</p>
        </div>

        <StartChallengeButton slug={challenge.slug} />
        <SubmissionForm challengeSlug={challenge.slug} />
      </aside>
    </div>
  );
}
