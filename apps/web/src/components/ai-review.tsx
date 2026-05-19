"use client";

import { PrReviewSchema, type PrReview } from "@prodready/shared/review";

const SEVERITY_STYLES: Record<string, string> = {
  minor: "bg-yellow-100 text-yellow-900",
  major: "bg-orange-100 text-orange-900",
  critical: "bg-red-100 text-red-900",
};

export function AiReview({ raw }: { raw: Record<string, unknown> }) {
  if (raw && "error" in raw && typeof raw.error === "string") {
    return (
      <p className="text-sm text-red-600">
        AI review unavailable: {raw.error}. Check OPENAI_API_KEY on the server.
      </p>
    );
  }

  const parsed = PrReviewSchema.safeParse(raw);
  if (!parsed.success) {
    return (
      <details className="text-sm">
        <summary className="cursor-pointer text-muted-foreground">
          Could not parse AI review (showing raw JSON).
        </summary>
        <pre className="mt-2 overflow-x-auto rounded-md bg-muted/30 p-3 text-xs">
          {JSON.stringify(raw, null, 2)}
        </pre>
      </details>
    );
  }

  const review: PrReview = parsed.data;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between rounded-lg border border-border p-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">AI score</p>
          <p className="text-3xl font-semibold">{review.score}/100</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            review.passed ? "bg-green-100 text-green-900" : "bg-red-100 text-red-900"
          }`}
        >
          {review.passed ? "Would pass review" : "Needs work"}
        </span>
      </div>

      <p className="text-sm">{review.summary}</p>

      {review.strengths.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Strengths
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {review.strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </section>
      )}

      {review.issues.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Issues
          </h3>
          <ul className="space-y-2">
            {review.issues.map((issue, i) => (
              <li key={i} className="rounded-md border border-border p-3 text-sm">
                <div className="mb-1 flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${SEVERITY_STYLES[issue.severity] ?? "bg-muted"}`}
                  >
                    {issue.severity}
                  </span>
                  <p className="font-medium">{issue.title}</p>
                </div>
                <p className="text-muted-foreground">{issue.suggestion}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {review.required_fixes.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Required fixes
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {review.required_fixes.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </section>
      )}

      {review.skills_practiced.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Skills practiced
          </h3>
          <p className="text-sm text-muted-foreground">{review.skills_practiced.join(" · ")}</p>
        </section>
      )}
    </div>
  );
}
