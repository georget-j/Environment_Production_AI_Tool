import { notFound } from "next/navigation";
import { apiFetch, type ChallengeDetail } from "@/lib/api";
import { Markdown } from "@/components/markdown";
import { CHALLENGE_CONFIG } from "@/lib/featured-files";
import { ChallengeView } from "@/components/challenge-view";

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

  // Pre-rendered (server) content for the left column: scenario, goal,
  // instructions, plus the per-mode quick-help cards and skills.
  const left = (
    <>
      <header className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {challenge.module.title}
        </p>
        <h1 className="text-2xl font-semibold leading-tight lg:text-3xl">{challenge.title}</h1>
        <p className="max-w-prose text-sm leading-relaxed text-foreground">{challenge.scenario}</p>
      </header>

      <section>
        <h2 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Goal
        </h2>
        <p className="max-w-prose text-sm leading-relaxed">{challenge.learner_goal}</p>
      </section>

      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Instructions
        </h2>
        <div className="max-w-prose rounded-md border border-border bg-muted/20 p-4">
          <Markdown>{challenge.instructions}</Markdown>
        </div>
      </section>

      {config?.mode === "pyodide" ? (
        <details className="rounded-md border border-border p-3 text-sm" open>
          <summary className="cursor-pointer text-sm font-semibold">How this works</summary>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
            <li>Edit the unlocked files in the workspace.</li>
            <li>Click <strong>Run tests</strong> — Python boots in your browser.</li>
            <li>Iterate until the tests pass.</li>
            <li>
              Stuck? Use the <strong>Hint</strong> buttons in the mentor sidebar, or click{" "}
              <strong>I&apos;m stuck — help</strong> in the result panel.
            </li>
            <li>Submit when green — your edits are saved as you go.</li>
          </ol>
        </details>
      ) : (
        <div className="rounded-md border border-border p-3 text-sm text-muted-foreground">
          Read through the files. Ask the mentor anything that isn&apos;t obvious.
        </div>
      )}

      <section className="rounded-md border border-border p-3">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Skills
        </h3>
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
      </section>
    </>
  );

  return (
    <div className="py-6">
      <ChallengeView
        challengeId={challenge.id}
        challengeSlug={challenge.slug}
        repoTemplateUrl={challenge.repo_template_url}
        repoBranch={challenge.repo_branch}
        config={config}
        left={left}
      />
    </div>
  );
}
