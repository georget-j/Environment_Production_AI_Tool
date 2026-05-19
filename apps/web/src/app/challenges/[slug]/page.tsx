import { notFound } from "next/navigation";
import { apiFetch, type ChallengeDetail } from "@/lib/api";
import { StartChallengeButton } from "@/components/start-challenge-button";
import { SubmissionForm } from "@/components/submission-form";
import { MentorChat } from "@/components/mentor-chat";
import { Markdown } from "@/components/markdown";
import { CodePreview } from "@/components/code-preview";
import { FEATURED_FILES } from "@/lib/featured-files";

type Params = Promise<{ slug: string }>;

export default async function ChallengeDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  let challenge: ChallengeDetail;
  try {
    challenge = await apiFetch<ChallengeDetail>(`/api/challenges/${slug}`);
  } catch {
    notFound();
  }

  const featuredFiles = FEATURED_FILES[challenge.slug] ?? [];
  const validation = challenge.validation_config_json as {
    tests?: string[];
    lint?: string[];
  };

  return (
    <div className="grid gap-8 py-8 lg:grid-cols-[3fr_2fr]">
      <article className="space-y-8">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            {challenge.module.title}
          </p>
          <h1 className="text-3xl font-semibold">{challenge.title}</h1>
          <p className="text-muted-foreground">{challenge.scenario}</p>
        </header>

        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Goal
          </h2>
          <p className="text-sm">{challenge.learner_goal}</p>
        </section>

        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Instructions
          </h2>
          <div className="rounded-md border border-border bg-muted/20 p-4">
            <Markdown>{challenge.instructions}</Markdown>
          </div>
        </section>

        <CodePreview
          repoTemplateUrl={challenge.repo_template_url}
          branch={challenge.repo_branch}
          paths={featuredFiles}
        />

        <MentorChat challengeId={challenge.id} />
      </article>

      <aside className="space-y-4">
        <div className="space-y-2 rounded-lg border border-border p-4">
          <h3 className="text-sm font-semibold">Repo</h3>
          {challenge.repo_template_url ? (
            <>
              <a
                href={
                  challenge.repo_branch
                    ? `${challenge.repo_template_url}/tree/${challenge.repo_branch}`
                    : challenge.repo_template_url
                }
                target="_blank"
                rel="noreferrer"
                className="block break-all text-sm text-blue-600 hover:underline"
              >
                {challenge.repo_template_url}
              </a>
              {challenge.repo_branch && (
                <p className="text-xs text-muted-foreground">
                  Branch: <code className="font-mono">{challenge.repo_branch}</code>
                </p>
              )}
              <p className="pt-1 text-xs text-muted-foreground">
                Fork it → clone → check out the branch → make pytest pass.
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">TBD</p>
          )}
        </div>

        <div className="space-y-2 rounded-lg border border-border p-4">
          <h3 className="text-sm font-semibold">How we check your work</h3>
          {validation.tests?.map((cmd) => (
            <pre key={cmd} className="rounded bg-muted/30 px-2 py-1 font-mono text-xs">
              {cmd}
            </pre>
          ))}
          {validation.lint?.map((cmd) => (
            <pre key={cmd} className="rounded bg-muted/30 px-2 py-1 font-mono text-xs">
              {cmd}
            </pre>
          ))}
        </div>

        <div className="space-y-2 rounded-lg border border-border p-4">
          <h3 className="text-sm font-semibold">Skills</h3>
          <div className="flex flex-wrap gap-1">
            {challenge.skills.map((s) => (
              <span
                key={s}
                className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
              >
                {s}
              </span>
            ))}
          </div>
        </div>

        <StartChallengeButton slug={challenge.slug} />
        <SubmissionForm challengeSlug={challenge.slug} />
      </aside>
    </div>
  );
}
