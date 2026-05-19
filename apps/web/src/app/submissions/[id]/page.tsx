"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { AiReview } from "@/components/ai-review";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Submission = {
  id: string;
  challenge_id: string;
  repo_url: string;
  commit_sha: string | null;
  passed: boolean;
  test_output: string | null;
  lint_output: string | null;
  ai_review_json: Record<string, unknown>;
  created_at: string;
};

type Params = Promise<{ id: string }>;

export default function SubmissionPage({ params }: { params: Params }) {
  const { id } = use(params);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function fetchOnce() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setError("Not signed in.");
        return false;
      }
      const response = await fetch(`${API_BASE_URL}/api/submissions/${id}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
        cache: "no-store",
      });
      if (!active) return true;
      if (!response.ok) {
        setError(`Could not load submission (${response.status})`);
        return true;
      }
      const data: Submission = await response.json();
      setSubmission(data);
      const reviewReady =
        data.ai_review_json && Object.keys(data.ai_review_json).length > 0;
      return reviewReady;
    }

    let timer: ReturnType<typeof setTimeout> | undefined;
    (async function poll() {
      const done = await fetchOnce();
      if (!active || done) return;
      timer = setTimeout(poll, 2000);
    })();

    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [id]);

  if (error) return <p className="py-8 text-sm text-red-600">{error}</p>;
  if (!submission) return <p className="py-8 text-sm text-muted-foreground">Loading…</p>;

  return (
    <div className="space-y-8 py-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">
          {submission.passed ? "Tests passed" : "Tests failed"}
        </h1>
        <p className="text-sm text-muted-foreground">
          Submitted{" "}
          <a
            href={submission.repo_url}
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 hover:underline"
          >
            {submission.repo_url}
          </a>{" "}
          {submission.commit_sha && (
            <>
              @ <code className="font-mono text-xs">{submission.commit_sha.slice(0, 7)}</code>
            </>
          )}
        </p>
      </header>

      <section>
        <h2 className="mb-2 text-sm font-semibold">Test output</h2>
        <pre className="overflow-x-auto rounded-md border border-border bg-muted/30 p-4 text-xs">
          {submission.test_output ?? "(none)"}
        </pre>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold">AI review</h2>
        {submission.ai_review_json && Object.keys(submission.ai_review_json).length > 0 ? (
          <AiReview raw={submission.ai_review_json} />
        ) : (
          <p className="text-sm text-muted-foreground">Generating…</p>
        )}
      </section>

      <Link href="/dashboard">
        <Button variant="outline">Back to dashboard</Button>
      </Link>
    </div>
  );
}
