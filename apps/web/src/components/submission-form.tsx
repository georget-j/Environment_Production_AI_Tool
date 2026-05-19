"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function SubmissionForm({ challengeSlug }: { challengeSlug: string }) {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [commitSha, setCommitSha] = useState("");
  const [testOutput, setTestOutput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);

    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session) {
      router.push(`/login?next=/challenges/${challengeSlug}`);
      return;
    }

    const response = await fetch(`${API_BASE_URL}/api/challenges/${challengeSlug}/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        repo_url: repoUrl,
        commit_sha: commitSha || undefined,
        test_output: testOutput || undefined,
      }),
    });

    setPending(false);
    if (!response.ok) {
      const body = await response.text();
      setError(`Submission failed (${response.status}): ${body.slice(0, 200)}`);
      return;
    }
    const data = await response.json();
    router.push(`/submissions/${data.id}`);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-border p-4">
      <h3 className="text-sm font-semibold">Submit your work</h3>
      <div className="space-y-2">
        <label className="block text-xs text-muted-foreground">Repo URL</label>
        <input
          type="url"
          required
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/you/your-fork"
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
        />
      </div>
      <div className="space-y-2">
        <label className="block text-xs text-muted-foreground">Commit SHA (optional)</label>
        <input
          type="text"
          pattern="[0-9a-f]{7,40}"
          value={commitSha}
          onChange={(e) => setCommitSha(e.target.value)}
          placeholder="e.g. 4f3a9c1"
          className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs"
        />
      </div>
      <div className="space-y-2">
        <label className="block text-xs text-muted-foreground">
          Paste your pytest output
        </label>
        <textarea
          required
          rows={6}
          value={testOutput}
          onChange={(e) => setTestOutput(e.target.value)}
          placeholder="5 passed in 0.42s"
          className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs"
        />
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <Button type="submit" disabled={pending} className="w-full">
        {pending ? "Submitting…" : "Submit"}
      </Button>
    </form>
  );
}
