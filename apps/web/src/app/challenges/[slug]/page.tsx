import { notFound } from "next/navigation";
import { apiFetch, type ChallengeDetail } from "@/lib/api";
import { MentorChat } from "@/components/mentor-chat";
import { Markdown } from "@/components/markdown";
import { CodePreview } from "@/components/code-preview";
import { ChallengeRunner } from "@/components/challenge-runner";
import { CHALLENGE_CONFIG } from "@/lib/featured-files";

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
  const branch = challenge.repo_branch ?? "main";
  const repoUrl = challenge.repo_template_url ?? "";

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

        {config?.mode === "pyodide" && repoUrl ? (
          <ChallengeRunner
            challengeSlug={challenge.slug}
            repoTemplateUrl={repoUrl}
            branch={branch}
            config={config}
          />
        ) : (
          <CodePreview
            repoTemplateUrl={challenge.repo_template_url}
            branch={challenge.repo_branch}
            paths={config?.mode === "reading" ? config.readonly : []}
          />
        )}

        <MentorChat challengeId={challenge.id} />
      </article>

      <aside className="space-y-4">
        {config?.mode === "pyodide" ? (
          <div className="space-y-2 rounded-lg border border-border p-4">
            <h3 className="text-sm font-semibold">How this works</h3>
            <ol className="list-decimal space-y-1 pl-4 text-xs text-muted-foreground">
              <li>Edit the unlocked files in the workspace.</li>
              <li>
                Click <strong>Run tests</strong> — Python boots in your browser.
              </li>
              <li>Iterate until the tests pass.</li>
              <li>Submit when green — your edits are saved as you go.</li>
            </ol>
          </div>
        ) : (
          <div className="space-y-2 rounded-lg border border-border p-4">
            <h3 className="text-sm font-semibold">How this works</h3>
            <p className="text-xs text-muted-foreground">
              Read through the files. Ask the mentor anything that isn&apos;t obvious. Submit by
              answering the mentor&apos;s closing question (a small reflection).
            </p>
          </div>
        )}

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

      </aside>
    </div>
  );
}
